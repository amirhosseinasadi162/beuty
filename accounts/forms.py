import re

from django import forms


PERSIAN_DIGITS = str.maketrans(
    "۰۱۲۳۴۵۶۷۸۹",
    "0123456789",
)

ARABIC_DIGITS = str.maketrans(
    "٠١٢٣٤٥٦٧٨٩",
    "0123456789",
)


def normalize_phone(phone):
    """
    Normalize user-entered phone numbers without assuming
    a specific country code.
    """
    phone = phone.translate(PERSIAN_DIGITS)
    phone = phone.translate(ARABIC_DIGITS)

    phone = phone.strip()

    for character in (" ", "-", "(", ")"):
        phone = phone.replace(character, "")

    if not re.fullmatch(r"\+?[0-9]{8,19}", phone):
        raise forms.ValidationError(
            "Please enter a valid phone number."
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
                "OTP code must contain only numbers."
            )

        return code