"use client";

import { useState, type FormEvent } from "react";
import Link from "next/link";
import {
  ArrowLeft,
  Eye,
  EyeOff,
  Phone,
  ShieldCheck,
} from "lucide-react";

import AuthShell from "@/components/auth/auth-shell";

export default function RegisterPage() {
  const [showPasswords, setShowPasswords] = useState(false);
  const [notice, setNotice] = useState("");

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    const formData = new FormData(event.currentTarget);
    const password = String(formData.get("password") ?? "");
    const confirmation = String(
      formData.get("password_confirm") ?? ""
    );

    if (password.length < 8) {
      setNotice("رمز عبور باید حداقل ۸ کاراکتر داشته باشد.");
      return;
    }

    if (password !== confirmation) {
      setNotice("رمز عبور و تکرار آن یکسان نیستند.");
      return;
    }

    setNotice(
      "فرم ثبت‌نام آماده است؛ بررسی شماره و ارسال OTP را در مرحله اتصال به Django انجام می‌دهیم."
    );
  }

  return (
    <AuthShell>
      <header className="auth-heading">
        <span className="auth-kicker">شروع یک تجربه تازه</span>

        <h2>حساب خودت را بساز</h2>

        <p>
          شماره موبایل و رمز شخصی خودت را مشخص کن. با تأیید
          شماره، ثبت‌نام کامل خواهد شد.
        </p>
      </header>

      <form className="auth-form" onSubmit={handleSubmit}>
        <div className="form-field">
          <label className="form-label" htmlFor="phone">
            شماره موبایل
          </label>

          <div className="form-input-wrap">
            <Phone
              className="form-input-icon"
              size={17}
              aria-hidden="true"
            />

            <input
              className="form-input"
              id="phone"
              name="phone"
              type="tel"
              placeholder="0912 123 4567"
              autoComplete="tel"
              inputMode="tel"
              dir="ltr"
              required
            />
          </div>
        </div>

        <div className="form-field">
          <label className="form-label" htmlFor="password">
            رمز عبور
          </label>

          <div className="form-input-wrap">
            <input
              className="form-input password-input"
              id="password"
              name="password"
              type={showPasswords ? "text" : "password"}
              placeholder="حداقل ۸ کاراکتر"
              autoComplete="new-password"
              minLength={8}
              dir="ltr"
              required
            />

            <button
              className="password-toggle"
              type="button"
              onClick={() =>
                setShowPasswords((value) => !value)
              }
              aria-label={
                showPasswords ? "مخفی کردن رمز" : "نمایش رمز"
              }
            >
              {showPasswords ? (
                <EyeOff size={15} aria-hidden="true" />
              ) : (
                <Eye size={15} aria-hidden="true" />
              )}

              {showPasswords ? "مخفی" : "نمایش"}
            </button>
          </div>
        </div>

        <div className="form-field">
          <label
            className="form-label"
            htmlFor="password_confirm"
          >
            تکرار رمز عبور
          </label>

          <div className="form-input-wrap">
            <input
              className="form-input password-input"
              id="password_confirm"
              name="password_confirm"
              type={showPasswords ? "text" : "password"}
              placeholder="رمز را دوباره وارد کن"
              autoComplete="new-password"
              minLength={8}
              dir="ltr"
              required
            />
          </div>
        </div>

        <button className="primary-button" type="submit">
          ادامه و دریافت کد
          <ArrowLeft size={17} aria-hidden="true" />
        </button>
      </form>

      <div className="auth-note">
        <ShieldCheck
          size={16}
          aria-hidden="true"
          style={{ display: "inline", verticalAlign: "middle" }}
        />{" "}
        رمز عبور واقعی باید در Backend اعتبارسنجی و به‌صورت امن
        ذخیره شود؛ بررسی مرورگر به‌تنهایی کافی نیست.
      </div>

      {notice && (
        <div className="auth-note" role="status" aria-live="polite">
          {notice}
        </div>
      )}

      <div className="auth-divider">
        <span>یا</span>
      </div>

      <div className="auth-switch">
        <span>قبلاً حساب ساخته‌ای؟</span>

        <Link className="auth-link" href="/">
          وارد شو
        </Link>
      </div>
    </AuthShell>
  );
}