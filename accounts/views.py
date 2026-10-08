from datetime import timedelta

from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.utils import timezone

from accounts.forms import OTPVerifyForm, PhoneForm
from accounts.models import OTPCode, User
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


AUTH_FLOW_SESSION_KEY = "pending_auth"


def _set_pending_auth(request, phone, purpose, otp_id):
    request.session[AUTH_FLOW_SESSION_KEY] = {
        "phone": phone,
        "purpose": purpose,
        "otp_id": otp_id,
    }

    request.session.modified = True


def _get_pending_auth(request):
    return request.session.get(
        AUTH_FLOW_SESSION_KEY
    )


def _clear_pending_auth(request):
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


def _get_verify_context(request, form, pending_auth):
    resend_available_in = 0

    otp = (
        OTPCode.objects
        .filter(
            id=pending_auth.get("otp_id"),
            phone=pending_auth["phone"],
            purpose=pending_auth["purpose"],
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
            resend_available_in = int(remaining) + 1

    return {
        "form": form,
        "phone": pending_auth["phone"],
        "display_phone": _mask_phone(
            pending_auth["phone"]
        ),
        "purpose": pending_auth["purpose"],
        "resend_available_in": resend_available_in,
    }


def _send_otp(
    request,
    form,
    purpose,
    template_name,
):
    if not form.is_valid():
        return render(
            request,
            template_name,
            {"form": form},
            status=400,
        )

    phone = form.cleaned_data["phone"]

    service = OTPService()

    try:
        otp = service.request_otp(
            phone=phone,
            purpose=purpose,
        )

    except OTPResendTooSoon as exc:
        form.add_error(
            "phone",
            f"لطفاً {exc.retry_after_seconds} ثانیه "
            "قبل از درخواست مجدد صبر کنید.",
        )

        return render(
            request,
            template_name,
            {"form": form},
            status=429,
        )

    _set_pending_auth(
        request=request,
        phone=phone,
        purpose=purpose,
        otp_id=otp.id,
    )

    return redirect(
        "accounts:verify_otp"
    )


def login_view(request):
    if request.user.is_authenticated:
        return redirect(
            "accounts:dashboard"
        )

    form = PhoneForm()

    return render(
        request,
        "accounts/login.html",
        {"form": form},
    )


def login_request_otp(request):
    if request.user.is_authenticated:
        return redirect(
            "accounts:dashboard"
        )

    if request.method != "POST":
        return redirect(
            "accounts:login"
        )

    form = PhoneForm(
        request.POST
    )

    return _send_otp(
        request=request,
        form=form,
        purpose=OTPCode.Purpose.LOGIN,
        template_name="accounts/login.html",
    )


def register_view(request):
    if request.user.is_authenticated:
        return redirect(
            "accounts:dashboard"
        )

    form = PhoneForm()

    return render(
        request,
        "accounts/register.html",
        {"form": form},
    )


def register_request_otp(request):
    if request.user.is_authenticated:
        return redirect(
            "accounts:dashboard"
        )

    if request.method != "POST":
        return redirect(
            "accounts:register"
        )

    form = PhoneForm(
        request.POST
    )

    return _send_otp(
        request=request,
        form=form,
        purpose=OTPCode.Purpose.REGISTRATION,
        template_name="accounts/register.html",
    )


def verify_otp(request):
    pending_auth = _get_pending_auth(request)

    if not pending_auth:
        messages.error(
            request,
            "جلسه تأیید منقضی شده است. دوباره درخواست کد کنید.",
        )

        return redirect(
            "accounts:login"
        )

    if request.method == "GET":
        form = OTPVerifyForm()

        return render(
            request,
            "accounts/verify_otp.html",
            _get_verify_context(
                request,
                form,
                pending_auth,
            ),
        )

    form = OTPVerifyForm(
        request.POST
    )

    if not form.is_valid():
        return render(
            request,
            "accounts/verify_otp.html",
            _get_verify_context(
                request,
                form,
                pending_auth,
            ),
            status=400,
        )

    service = OTPService()

    try:
        service.verify_otp(
            phone=pending_auth["phone"],
            purpose=pending_auth["purpose"],
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
            _get_verify_context(
                request,
                form,
                pending_auth,
            ),
            status=400,
        )

    except OTPExpired:
        form.add_error(
            "code",
            "این کد منقضی شده است. کد جدید دریافت کنید.",
        )

        return render(
            request,
            "accounts/verify_otp.html",
            _get_verify_context(
                request,
                form,
                pending_auth,
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
            _get_verify_context(
                request,
                form,
                pending_auth,
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
            _get_verify_context(
                request,
                form,
                pending_auth,
            ),
            status=400,
        )

    except OTPNotFound:
        _clear_pending_auth(request)

        messages.error(
            request,
            "درخواست تأیید معتبر نیست. دوباره شروع کنید.",
        )

        return redirect(
            "accounts:login"
        )

    phone = pending_auth["phone"]
    purpose = pending_auth["purpose"]

    _clear_pending_auth(request)

    # -----------------------------
    # Registration
    # -----------------------------
    if purpose == OTPCode.Purpose.REGISTRATION:

        existing_user = User.objects.filter(
            phone=phone,
        ).first()

        if existing_user:
            messages.info(
                request,
                "این شماره قبلاً ثبت شده است. "
                "برای ورود از صفحه ورود استفاده کنید.",
            )

            return redirect(
                "accounts:login"
            )

        user = User.objects.create(
            phone=phone,
            phone_verified=True,
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
            "accounts:dashboard"
        )

    # -----------------------------
    # Login
    # -----------------------------
    user = User.objects.filter(
        phone=phone,
    ).first()

    if not user:
        messages.info(
            request,
            "حسابی با این شماره پیدا نشد. ابتدا ثبت‌نام کنید.",
        )

        return redirect(
            "accounts:register"
        )

    if not user.phone_verified:
        user.phone_verified = True

        user.save(
            update_fields=[
                "phone_verified"
            ]
        )

    _login_user(
        request,
        user,
    )

    messages.success(
        request,
        "با موفقیت وارد شدید.",
    )

    return redirect(
        "accounts:dashboard"
    )


def resend_otp(request):
    if request.method != "POST":
        return redirect(
            "accounts:login"
        )

    pending_auth = _get_pending_auth(request)

    if not pending_auth:
        messages.error(
            request,
            "جلسه تأیید شما منقضی شده است.",
        )

        return redirect(
            "accounts:login"
        )

    service = OTPService()

    try:
        otp = service.request_otp(
            phone=pending_auth["phone"],
            purpose=pending_auth["purpose"],
        )

    except OTPResendTooSoon as exc:
        form = OTPVerifyForm()

        context = _get_verify_context(
            request,
            form,
            pending_auth,
        )

        context["resend_error"] = (
            f"لطفاً {exc.retry_after_seconds} ثانیه دیگر صبر کنید."
        )

        return render(
            request,
            "accounts/verify_otp.html",
            context,
            status=429,
        )

    _set_pending_auth(
        request=request,
        phone=pending_auth["phone"],
        purpose=pending_auth["purpose"],
        otp_id=otp.id,
    )

    messages.success(
        request,
        "کد جدید ارسال شد.",
    )

    return redirect(
        "accounts:verify_otp"
    )


@login_required
def dashboard(request):
    return render(
        request,
        "accounts/dashboard.html",
    )


def logout_view(request):
    if request.method == "POST":
        logout(request)

    return redirect(
        "accounts:login"
    )