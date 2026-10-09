import re

from django import forms
from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import (
    password_validators_help_texts,
    validate_password,
)
from django.core.exceptions import ValidationError

from accounts.models import User


PERSIAN_DIGITS = str.maketrans(
    "۰۱۲۳۴۵۶۷۸۹",
    "0123456789",
)

ARABIC_DIGITS = str.maketrans(
    "٠١٢٣٤٥٦٧٨٩",
    "0123456789",
)


def normalize_phone(phone):
    phone = phone.translate(PERSIAN_DIGITS)
    phone = phone.translate(ARABIC_DIGITS)

    phone = phone.strip()

    for character in (" ", "-", "(", ")"):
        phone = phone.replace(character, "")

    if not re.fullmatch(r"\+?[0-9]{8,19}", phone):
        raise forms.ValidationError(
            "شماره موبایل وارد شده معتبر نیست."
        )

    return phone


class PhoneForm(forms.Form):
    phone = forms.CharField(
        max_length=20,
        required=True,
    )

    def clean_phone(self):
        return normalize_phone(
            self.cleaned_data["phone"]
        )


class LoginForm(PhoneForm):
    password = forms.CharField(
        required=True,
        widget=forms.PasswordInput(
            attrs={
                "autocomplete": "current-password",
            }
        ),
    )

    def __init__(self, *args, request=None, **kwargs):
        super().__init__(*args, **kwargs)

        self.request = request
        self.user_cache = None

    def clean(self):
        cleaned_data = super().clean()

        phone = cleaned_data.get("phone")
        password = cleaned_data.get("password")

        if not phone or not password:
            return cleaned_data

        self.user_cache = authenticate(
            self.request,
            phone=phone,
            password=password,
        )

        if (
            self.user_cache is None
            or not self.user_cache.is_active
            or not self.user_cache.phone_verified
        ):
            raise forms.ValidationError(
                "شماره موبایل یا رمز عبور صحیح نیست."
            )

        return cleaned_data

    def get_user(self):
        return self.user_cache


class RegisterForm(PhoneForm):
    password = forms.CharField(
        required=True,
        min_length=8,
        widget=forms.PasswordInput(
            attrs={
                "autocomplete": "new-password",
            }
        ),
    )

    password_confirm = forms.CharField(
        required=True,
        widget=forms.PasswordInput(
            attrs={
                "autocomplete": "new-password",
            }
        ),
    )

    def clean(self):
        cleaned_data = super().clean()

        phone = cleaned_data.get("phone")
        password = cleaned_data.get("password")
        password_confirm = cleaned_data.get(
            "password_confirm"
        )

        if (
            password
            and password_confirm
            and password != password_confirm
        ):
            self.add_error(
                "password_confirm",
                "تکرار رمز عبور با رمز اصلی یکسان نیست.",
            )

        if password:
            temporary_user = User(
                phone=phone or "",
            )

            try:
                validate_password(
                    password,
                    user=temporary_user,
                )
            except ValidationError as exc:
                self.add_error(
                    "password",
                    exc,
                )

        return cleaned_data

    @property
    def password_help_texts(self):
        return password_validators_help_texts()


class OTPVerifyForm(forms.Form):
    code = forms.CharField(
        max_length=6,
        min_length=6,
        required=True,
    )

    def clean_code(self):
        code = self.cleaned_data["code"].strip()

        if not code.isdigit():
            raise forms.ValidationError(
                "کد تأیید باید فقط شامل عدد باشد."
            )

        return code