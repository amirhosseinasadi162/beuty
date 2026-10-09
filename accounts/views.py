from datetime import timedelta

from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.hashers import make_password
from django.db import transaction
from django.shortcuts import redirect, render
from django.utils import timezone

from accounts.forms import (
    LoginForm,
    OTPVerifyForm,
    RegisterForm,
)
from accounts.models import (
    OTPCode,
    RegistrationAttempt,
    User,
)
from accounts.services.otp import (
    OTPAlreadyVerified,
    OTPExpired,
    OTPInvalid,
    OTPNotFound,
    OTPResendTooSoon,
    OTPService,
    OTPTooManyAttempts,
    OTP_RESEND_COOLDOWN_SECONDS,
)


AUTH_FLOW_SESSION_KEY = "pending_registration"

REGISTRATION_ATTEMPT_TTL_SECONDS = 10 * 60


def _set_pending_registration(
    request,
    phone,
    otp_id,
    attempt_id,
):
    request.session[
        AUTH_FLOW_SESSION_KEY
    ] = {
        "phone": phone,
        "otp_id": otp_id,
        "attempt_id": attempt_id,
        "purpose": OTPCode.Purpose.REGISTRATION,
    }

    request.session.modified = True


def _get_pending_registration(request):
    return request.session.get(
        AUTH_FLOW_SESSION_KEY
    )


def _clear_pending_registration(request):
    request.session.pop(
        AUTH_FLOW_SESSION_KEY,
        None,
    )


def _login_user(request, user):
    login(
        request,
        user,
        backend="django.contrib.auth.backends.ModelBackend",
    )


def _mask_phone(phone):
    if len(phone) <= 7:
        return phone

    return f"{phone[:4]}••••{phone[-3:]}"


def _verify_context(
    request,
    form,
    pending_registration,
):
    resend_available_in = 0

    otp = (
        OTPCode.objects
        .filter(
            id=pending_registration.get("otp_id"),
            phone=pending_registration["phone"],
            purpose=OTPCode.Purpose.REGISTRATION,
        )
        .first()
    )

    if otp:
        available_at = (
            otp.created_at
            + timedelta(
                seconds=OTP_RESEND_COOLDOWN_SECONDS
            )
        )

        remaining = (
            available_at - timezone.now()
        ).total_seconds()

        if remaining > 0:
            resend_available_in = (
                int(remaining) + 1
            )

    return {
        "form": form,
        "phone": pending_registration["phone"],
        "display_phone": _mask_phone(
            pending_registration["phone"]
        ),
        "resend_available_in": (
            resend_available_in
        ),
    }


# -----------------------------------------
# Entry
# -----------------------------------------

def entrypoint(request):
    if request.user.is_authenticated:
        return redirect("accounts:home")

    return redirect("accounts:login")


# -----------------------------------------
# Login
# -----------------------------------------

def login_view(request):
    if request.user.is_authenticated:
        return redirect("accounts:home")

    if request.method == "POST":
        form = LoginForm(
            request.POST,
            request=request,
        )

        if form.is_valid():
            _login_user(
                request,
                form.get_user(),
            )

            return redirect(
                "accounts:home"
            )
    else:
        form = LoginForm()

    return render(
        request,
        "accounts/login.html",
        {
            "form": form,
        },
    )


# -----------------------------------------
# Registration
# -----------------------------------------

def register_view(request):
    if request.user.is_authenticated:
        return redirect("accounts:home")

    if request.method == "POST":
        form = RegisterForm(
            request.POST,
        )

        if form.is_valid():

            phone = form.cleaned_data["phone"]
            password = form.cleaned_data["password"]

            service = OTPService()

            try:
                otp = service.request_otp(
                    phone=phone,
                    purpose=OTPCode.Purpose.REGISTRATION,
                )

            except OTPResendTooSoon as exc:
                form.add_error(
                    "phone",
                    (
                        f"لطفاً {exc.retry_after_seconds} "
                        "ثانیه قبل از درخواست مجدد صبر کنید."
                    ),
                )

                return render(
                    request,
                    "accounts/register.html",
                    {
                        "form": form,
                        "password_help_texts": (
                            form.password_help_texts
                        ),
                    },
                    status=429,
                )

            attempt, _ = (
                RegistrationAttempt.objects.update_or_create(
                    phone=phone,
                    defaults={
                        "password_hash": make_password(
                            password
                        ),
                        "expires_at": (
                            timezone.now()
                            + timedelta(
                                seconds=(
                                    REGISTRATION_ATTEMPT_TTL_SECONDS
                                )
                            )
                        ),
                    },
                )
            )

            _set_pending_registration(
                request=request,
                phone=phone,
                otp_id=otp.id,
                attempt_id=attempt.id,
            )

            return redirect(
                "accounts:verify_otp"
            )

    else:
        form = RegisterForm()

    return render(
        request,
        "accounts/register.html",
        {
            "form": form,
            "password_help_texts": (
                form.password_help_texts
            ),
        },
    )


# -----------------------------------------
# OTP Verification
# -----------------------------------------

def verify_otp(request):
    pending = _get_pending_registration(
        request
    )

    if not pending:
        messages.error(
            request,
            "جلسه ثبت‌نام منقضی شده است. دوباره شروع کنید.",
        )

        return redirect(
            "accounts:register"
        )

    if request.method == "GET":
        form = OTPVerifyForm()

        return render(
            request,
            "accounts/verify_otp.html",
            _verify_context(
                request,
                form,
                pending,
            ),
        )

    form = OTPVerifyForm(
        request.POST
    )

    if not form.is_valid():
        return render(
            request,
            "accounts/verify_otp.html",
            _verify_context(
                request,
                form,
                pending,
            ),
            status=400,
        )

    service = OTPService()

    try:
        service.verify_otp(
            phone=pending["phone"],
            purpose=OTPCode.Purpose.REGISTRATION,
            code=form.cleaned_data["code"],
        )

    except OTPInvalid:
        form.add_error(
            "code",
            "کد وارد شده صحیح نیست.",
        )

        return render(
            request,
            "accounts/verify_otp.html",
            _verify_context(
                request,
                form,
                pending,
            ),
            status=400,
        )

    except OTPExpired:
        form.add_error(
            "code",
            "کد تأیید منقضی شده است. کد جدید دریافت کنید.",
        )

        return render(
            request,
            "accounts/verify_otp.html",
            _verify_context(
                request,
                form,
                pending,
            ),
            status=400,
        )

    except OTPTooManyAttempts:
        form.add_error(
            "code",
            "تعداد تلاش‌های مجاز تمام شده است. کد جدید دریافت کنید.",
        )

        return render(
            request,
            "accounts/verify_otp.html",
            _verify_context(
                request,
                form,
                pending,
            ),
            status=429,
        )

    except OTPAlreadyVerified:
        form.add_error(
            "code",
            "این کد قبلاً استفاده شده است.",
        )

        return render(
            request,
            "accounts/verify_otp.html",
            _verify_context(
                request,
                form,
                pending,
            ),
            status=400,
        )

    except OTPNotFound:
        _clear_pending_registration(
            request
        )

        messages.error(
            request,
            "درخواست تأیید معتبر نیست. دوباره ثبت‌نام را شروع کنید.",
        )

        return redirect(
            "accounts:register"
        )

    attempt_id = pending["attempt_id"]
    phone = pending["phone"]

    with transaction.atomic():

        attempt = (
            RegistrationAttempt.objects
            .select_for_update()
            .filter(
                id=attempt_id,
                phone=phone,
            )
            .first()
        )

        if not attempt:
            _clear_pending_registration(
                request
            )

            messages.error(
                request,
                "اطلاعات ثبت‌نام دیگر معتبر نیست.",
            )

            return redirect(
                "accounts:register"
            )

        if attempt.is_expired:
            attempt.delete()

            _clear_pending_registration(
                request
            )

            messages.error(
                request,
                "زمان ثبت‌نام به پایان رسیده است.",
            )

            return redirect(
                "accounts:register"
            )

        user = (
            User.objects
            .select_for_update()
            .filter(phone=phone)
            .first()
        )

        # شماره قبلاً ثبت شده است.
        if user and user.phone_verified:

            attempt.delete()

            _clear_pending_registration(
                request
            )

            messages.info(
                request,
                "این شماره قبلاً ثبت شده است. "
                "برای ورود از صفحه ورود استفاده کنید.",
            )

            return redirect(
                "accounts:login"
            )

        # اگر یک ثبت‌نام ناقص قدیمی وجود داشته باشد،
        # همان حساب تکمیل می‌شود.
        if user:
            user.password = attempt.password_hash
            user.phone_verified = True
            user.is_active = True

            user.save(
                update_fields=[
                    "password",
                    "phone_verified",
                    "is_active",
                ]
            )

        else:
            user = User.objects.create(
                phone=phone,
                password=attempt.password_hash,
                phone_verified=True,
                is_active=True,
            )

        attempt.delete()

    _clear_pending_registration(
        request
    )

    _login_user(
        request,
        user,
    )

    messages.success(
        request,
        "حساب شما با موفقیت ایجاد شد.",
    )

    return redirect(
        "accounts:home"
    )


# -----------------------------------------
# Resend OTP
# -----------------------------------------

def resend_otp(request):
    if request.method != "POST":
        return redirect(
            "accounts:register"
        )

    pending = _get_pending_registration(
        request
    )

    if not pending:
        messages.error(
            request,
            "جلسه ثبت‌نام شما منقضی شده است.",
        )

        return redirect(
            "accounts:register"
        )

    service = OTPService()

    try:
        otp = service.request_otp(
            phone=pending["phone"],
            purpose=OTPCode.Purpose.REGISTRATION,
        )

    except OTPResendTooSoon as exc:
        form = OTPVerifyForm()

        context = _verify_context(
            request,
            form,
            pending,
        )

        context["resend_error"] = (
            f"لطفاً {exc.retry_after_seconds} "
            "ثانیه دیگر صبر کنید."
        )

        return render(
            request,
            "accounts/verify_otp.html",
            context,
            status=429,
        )

    RegistrationAttempt.objects.filter(
        id=pending["attempt_id"],
        phone=pending["phone"],
    ).update(
        expires_at=(
            timezone.now()
            + timedelta(
                seconds=(
                    REGISTRATION_ATTEMPT_TTL_SECONDS
                )
            )
        )
    )

    _set_pending_registration(
        request=request,
        phone=pending["phone"],
        otp_id=otp.id,
        attempt_id=pending["attempt_id"],
    )

    messages.success(
        request,
        "کد جدید ارسال شد.",
    )

    return redirect(
        "accounts:verify_otp"
    )


# -----------------------------------------
# Home
# -----------------------------------------

@login_required
def home(request):
    return render(
        request,
        "accounts/home.html",
    )


# -----------------------------------------
# Logout
# -----------------------------------------

def logout_view(request):
    if request.method == "POST":
        logout(request)

    return redirect(
        "accounts:login"
    )