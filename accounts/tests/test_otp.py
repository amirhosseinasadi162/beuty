from datetime import timedelta

from django.test import TestCase
from django.utils import timezone

from accounts.models import OTPCode
from accounts.services.otp import (
    OTPAlreadyVerified,
    OTPExpired,
    OTPInvalid,
    OTPNotFound,
    OTPResendTooSoon,
    OTPService,
    OTPTooManyAttempts,
)


class FakeOTPProvider:
    def __init__(self):
        self.sent_messages = []

    def send_otp(self, phone, code, purpose):
        self.sent_messages.append(
            {
                "phone": phone,
                "code": code,
                "purpose": purpose,
            }
        )


class OTPServiceTests(TestCase):
    def setUp(self):
        self.phone = "09102413908"
        self.purpose = OTPCode.Purpose.LOGIN
        self.provider = FakeOTPProvider()
        self.service = OTPService(provider=self.provider)

    def create_otp(self, code="374499"):
        otp = self.service.request_otp(
            phone=self.phone,
            purpose=self.purpose,
        )

        return otp, code

    def test_request_otp_creates_hashed_otp(self):
        otp, _ = self.create_otp()

        self.assertEqual(len(self.provider.sent_messages), 1)

        sent_code = self.provider.sent_messages[0]["code"]

        self.assertEqual(
            self.provider.sent_messages[0]["phone"],
            self.phone,
        )

        self.assertEqual(
            self.provider.sent_messages[0]["purpose"],
            self.purpose,
        )

        self.assertNotEqual(
            otp.code_hash,
            sent_code,
        )

        self.assertTrue(
            len(sent_code) == 6
        )

        self.assertTrue(
            sent_code.isdigit()
        )

    def test_correct_otp_verifies_successfully(self):
        otp = self.service.request_otp(
            phone=self.phone,
            purpose=self.purpose,
        )

        sent_code = self.provider.sent_messages[0]["code"]

        result = self.service.verify_otp(
            phone=self.phone,
            purpose=self.purpose,
            code=sent_code,
        )

        otp.refresh_from_db()

        self.assertEqual(result.pk, otp.pk)
        self.assertIsNotNone(otp.verified_at)
        self.assertEqual(otp.attempts, 0)

    def test_invalid_otp_increments_attempts(self):
        otp = self.service.request_otp(
            phone=self.phone,
            purpose=self.purpose,
        )

        with self.assertRaises(OTPInvalid):
            self.service.verify_otp(
                phone=self.phone,
                purpose=self.purpose,
                code="000000",
            )

        otp.refresh_from_db()

        self.assertEqual(otp.attempts, 1)
        self.assertIsNone(otp.verified_at)


    def test_fifth_invalid_attempt_locks_otp(self):
        otp = self.service.request_otp(
            phone=self.phone,
            purpose=self.purpose,
        )
    
        for _ in range(4):
            with self.assertRaises(OTPInvalid):
                self.service.verify_otp(
                    phone=self.phone,
                    purpose=self.purpose,
                    code="000000",
                )
    
        with self.assertRaises(OTPTooManyAttempts):
            self.service.verify_otp(
                phone=self.phone,
                purpose=self.purpose,
                code="000000",
            )
    
        otp.refresh_from_db()
    
        self.assertEqual(otp.attempts, 5)

    def test_locked_otp_cannot_be_verified_even_with_correct_code(self):
        self.service.request_otp(
            phone=self.phone,
            purpose=self.purpose,
        )

        correct_code = self.provider.sent_messages[0]["code"]

        for _ in range(5):
            try:
                self.service.verify_otp(
                    phone=self.phone,
                    purpose=self.purpose,
                    code="000000",
                )
            except (OTPInvalid, OTPTooManyAttempts):
                pass

        with self.assertRaises(OTPTooManyAttempts):
            self.service.verify_otp(
                phone=self.phone,
                purpose=self.purpose,
                code=correct_code,
            )

    def test_expired_otp_is_rejected(self):
        otp = self.service.request_otp(
            phone=self.phone,
            purpose=self.purpose,
        )

        correct_code = self.provider.sent_messages[0]["code"]

        OTPCode.objects.filter(pk=otp.pk).update(
            expires_at=timezone.now() - timedelta(seconds=1)
        )

        with self.assertRaises(OTPExpired):
            self.service.verify_otp(
                phone=self.phone,
                purpose=self.purpose,
                code=correct_code,
            )

        otp.refresh_from_db()

        self.assertIsNone(otp.verified_at)

    def test_verified_otp_cannot_be_verified_again(self):
        self.service.request_otp(
            phone=self.phone,
            purpose=self.purpose,
        )

        correct_code = self.provider.sent_messages[0]["code"]

        self.service.verify_otp(
            phone=self.phone,
            purpose=self.purpose,
            code=correct_code,
        )

        with self.assertRaises(OTPAlreadyVerified):
            self.service.verify_otp(
                phone=self.phone,
                purpose=self.purpose,
                code=correct_code,
            )

    def test_resend_is_blocked_during_cooldown(self):
        otp = self.service.request_otp(
            phone=self.phone,
            purpose=self.purpose,
        )

        with self.assertRaises(OTPResendTooSoon) as context:
            self.service.request_otp(
                phone=self.phone,
                purpose=self.purpose,
            )

        self.assertGreater(
            context.exception.retry_after_seconds,
            0,
        )

        self.assertLessEqual(
            context.exception.retry_after_seconds,
            60,
        )

        self.assertEqual(
            OTPCode.objects.filter(
                phone=self.phone,
                purpose=self.purpose,
            ).count(),
            1,
        )

    def test_new_otp_replaces_previous_for_verification(self):
        first_otp = self.service.request_otp(
            phone=self.phone,
            purpose=self.purpose,
        )

        first_code = self.provider.sent_messages[0]["code"]

        OTPCode.objects.filter(pk=first_otp.pk).update(
            created_at=timezone.now() - timedelta(seconds=61)
        )

        second_otp = self.service.request_otp(
            phone=self.phone,
            purpose=self.purpose,
        )

        second_code = self.provider.sent_messages[1]["code"]

        self.assertNotEqual(
            first_code,
            second_code,
        )

        self.assertEqual(
            OTPCode.objects.filter(
                phone=self.phone,
                purpose=self.purpose,
            ).count(),
            2,
        )

        with self.assertRaises(OTPInvalid):
            self.service.verify_otp(
                phone=self.phone,
                purpose=self.purpose,
                code=first_code,
            )

        result = self.service.verify_otp(
            phone=self.phone,
            purpose=self.purpose,
            code=second_code,
        )

        self.assertEqual(
            result.pk,
            second_otp.pk,
        )

    def test_otp_request_for_different_phone_is_not_found(self):
        self.service.request_otp(
            phone=self.phone,
            purpose=self.purpose,
        )

        code = self.provider.sent_messages[0]["code"]

        with self.assertRaises(OTPNotFound):
            self.service.verify_otp(
                phone="09120000000",
                purpose=self.purpose,
                code=code,
            )

    def test_otp_request_for_different_purpose_is_not_found(self):
        self.service.request_otp(
            phone=self.phone,
            purpose=self.purpose,
        )

        code = self.provider.sent_messages[0]["code"]

        with self.assertRaises(OTPNotFound):
            self.service.verify_otp(
                phone=self.phone,
                purpose=OTPCode.Purpose.REGISTRATION,
                code=code,
            )