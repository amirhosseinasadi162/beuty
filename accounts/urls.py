from django.urls import path

from . import views


app_name = "accounts"


urlpatterns = [
    path(
        "login/",
        views.login_view,
        name="login",
    ),
    path(
        "login/request-otp/",
        views.login_request_otp,
        name="login_request_otp",
    ),

    path(
        "register/",
        views.register_view,
        name="register",
    ),
    path(
        "register/request-otp/",
        views.register_request_otp,
        name="register_request_otp",
    ),

    path(
        "verify-otp/",
        views.verify_otp,
        name="verify_otp",
    ),
    path(
        "verify-otp/resend/",
        views.resend_otp,
        name="resend_otp",
    ),

    path(
        "dashboard/",
        views.dashboard,
        name="dashboard",
    ),
    path(
        "logout/",
        views.logout_view,
        name="logout",
    ),
]