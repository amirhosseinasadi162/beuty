from abc import ABC, abstractmethod

from django.conf import settings


class OTPProvider(ABC):
    @abstractmethod
    def send_otp(self, phone, code, purpose):
        raise NotImplementedError


class ConsoleOTPProvider(OTPProvider):
    def send_otp(self, phone, code, purpose):
        if not settings.DEBUG:
            raise RuntimeError(
                "ConsoleOTPProvider can only be used when DEBUG=True."
            )

        print()
        print("=" * 50)
        print("OTP MESSAGE")
        print(f"Phone: {phone}")
        print(f"Purpose: {purpose}")
        print(f"OTP Code: {code}")
        print("=" * 50)
        print()