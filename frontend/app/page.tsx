"use client";

import { useState, type FormEvent } from "react";
import Link from "next/link";
import {
  ArrowLeft,
  Eye,
  EyeOff,
  Phone,
} from "lucide-react";

import AuthShell from "@/components/auth/auth-shell";

export default function LoginPage() {
  const [showPassword, setShowPassword] = useState(false);
  const [notice, setNotice] = useState("");

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    setNotice(
      "رابط ورود آماده است؛ اتصال امن به API جنگو را در مرحله بعد انجام می‌دهیم."
    );
  }

  return (
    <AuthShell>
      <header className="auth-heading">
        <span className="auth-kicker">خوش برگشتی</span>

        <h2>وارد حساب خودت شو</h2>

        <p>
          شماره موبایل و رمز شخصی خودت را وارد کن تا وارد Beauty
          Booking شوی.
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
              type={showPassword ? "text" : "password"}
              placeholder="رمز عبور خود را وارد کن"
              autoComplete="current-password"
              dir="ltr"
              required
            />

            <button
              className="password-toggle"
              type="button"
              onClick={() => setShowPassword((value) => !value)}
              aria-label={
                showPassword ? "مخفی کردن رمز" : "نمایش رمز"
              }
            >
              {showPassword ? (
                <EyeOff size={15} aria-hidden="true" />
              ) : (
                <Eye size={15} aria-hidden="true" />
              )}

              {showPassword ? "مخفی" : "نمایش"}
            </button>
          </div>
        </div>

        <button className="primary-button" type="submit">
          ورود به حساب
          <ArrowLeft size={17} aria-hidden="true" />
        </button>
      </form>

      {notice && (
        <div className="auth-note" role="status" aria-live="polite">
          {notice}
        </div>
      )}

      <div className="auth-divider">
        <span>یا</span>
      </div>

      <div className="auth-switch">
        <span>هنوز حساب کاربری نداری؟</span>

        <Link className="auth-link" href="/register">
          ثبت‌نام کن
        </Link>
      </div>
    </AuthShell>
  );
}