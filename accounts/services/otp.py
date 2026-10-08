import secrets
from datetime import timedelta

from django.contrib.auth.hashers import check_password, make_password
from django.db import transaction
from django.utils import timezone

from accounts.models import OTPCode
from accounts.providers.otp import ConsoleOTPProvider


OTP_LENGTH = 6
OTP_TTL_SECONDS = 120
OTP_MAX_ATTEMPTS = 5
OTP_RESEND_COOLDOWN_SECONDS = 60


class OTPError(Exception):
    """Base exception for OTP-related errors."""


class OTPResendTooSoon(OTPError):
    def __init__(self, retry_after_seconds):
        self.retry_after_seconds = retry_after_seconds

        super().__init__(
            f"Please wait {retry_after_seconds} seconds before requesting another OTP."
        )


class OTPNotFound(OTPError):
    pass


class OTPExpired(OTPError):
    pass


class OTPTooManyAttempts(OTPError):
    pass


class OTPAlreadyVerified(OTPError):
    pass


class OTPInvalid(OTPError):
    pass


class OTPService:
    def __init__(self, provider=None):
        self.provider = provider or ConsoleOTPProvider()

    @staticmethod
    def generate_code():
        return f"{secrets.randbelow(1_000_000):06d}"

    def request_otp(self, phone, purpose):
        phone = phone.strip()

        now = timezone.now()

        latest_otp = (
            OTPCode.objects
            .filter(
                phone=phone,
                purpose=purpose,
            )
            .order_by("-created_at")
            .first()
        )

        if latest_otp:
            cooldown_until = (
                latest_otp.created_at
                + timedelta(seconds=OTP_RESEND_COOLDOWN_SECONDS)
            )

            if now < cooldown_until:
                retry_after = int(
                    (cooldown_until - now).total_seconds()
                )

                raise OTPResendTooSoon(
                    max(retry_after, 1)
                )

        code = self.generate_code()

        otp = OTPCode.objects.create(
            phone=phone,
            code_hash=make_password(code),
            purpose=purpose,
            expires_at=now + timedelta(seconds=OTP_TTL_SECONDS),
        )

        try:
            self.provider.send_otp(
                phone=phone,
                code=code,
                purpose=purpose,
            )
        except Exception:
            otp.delete()
            raise

        return otp

    def verify_otp(self, phone, purpose, code):
        phone = phone.strip()
        code = code.strip()
    
        invalid_attempts = None
    
        with transaction.atomic():
            otp = (
                OTPCode.objects
                .select_for_update()
                .filter(
                    phone=phone,
                    purpose=purpose,
                )
                .order_by("-created_at")
                .first()
            )
    
            if not otp:
                raise OTPNotFound(
                    "No OTP request was found."
                )
    
            if otp.verified_at is not None:
                raise OTPAlreadyVerified(
                    "This OTP has already been verified."
                )
    
            if otp.expires_at <= timezone.now():
                raise OTPExpired(
                    "This OTP has expired."
                )
    
            if otp.attempts >= OTP_MAX_ATTEMPTS:
                raise OTPTooManyAttempts(
                    "Too many verification attempts."
                )
    
            if not check_password(code, otp.code_hash):
                otp.attempts += 1
    
                otp.save(
                    update_fields=["attempts"],
                )
    
                invalid_attempts = otp.attempts
    
            else:
                otp.verified_at = timezone.now()
    
                otp.save(
                    update_fields=["verified_at"],
                )
    
        # Important:
        # The transaction must commit before raising an exception.
        if invalid_attempts is not None:
            if invalid_attempts >= OTP_MAX_ATTEMPTS:
                raise OTPTooManyAttempts(
                    "Too many verification attempts."
                )
    
            raise OTPInvalid(
                "Invalid OTP code."
            )
    
        return otp