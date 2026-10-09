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
        "register/",
        views.register_view,
        name="register",
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
        "home/",
        views.home,
        name="home",
    ),

    path(
        "logout/",
        views.logout_view,
        name="logout",
    ),
]