import type { ReactNode } from "react";
import Link from "next/link";
import {
  CalendarCheck,
  CheckCircle2,
  Sparkles,
  Star,
} from "lucide-react";

type AuthShellProps = {
  children: ReactNode;
};

export default function AuthShell({
  children,
}: AuthShellProps) {
  return (
    <main className="auth-stage">
      <div className="auth-card">
        <aside className="auth-visual">
          <Link href="/" className="auth-brand">
            <span className="auth-brand-mark">BB</span>
            <span>Beauty Booking</span>
          </Link>

          <div className="auth-hero">
            <span className="auth-eyebrow">
              <Sparkles size={14} aria-hidden="true" />
              زیبایی، با خیال راحت
            </span>

            <h1>
              دنیای زیبایی
              <span>همین‌جا شروع می‌شود</span>
            </h1>

            <p>
              سالن مورد علاقه‌ات را پیدا کن، متخصص مناسب را انتخاب کن
              و تجربه‌ی زیبایی خودت را ساده‌تر مدیریت کن.
            </p>

            <div className="auth-features">
              <span className="auth-feature">
                <CheckCircle2 size={13} />
                تجربه‌ای ساده
              </span>

              <span className="auth-feature">
                <CalendarCheck size={13} />
                مدیریت نوبت
              </span>

              <span className="auth-feature">
                <Star size={13} />
                دنیای زیبایی
              </span>
            </div>
          </div>

          <div className="auth-preview">
            <div className="auth-preview-icon">
              <Sparkles size={19} />
            </div>

            <div>
              <strong>Beauty, made personal</strong>
              <small>
                فضایی برای مشتریان، سالن‌ها و متخصصان زیبایی
              </small>
            </div>
          </div>
        </aside>

        <section className="auth-panel">
          <div className="auth-panel-inner">
            {children}

            <footer className="auth-footer">
              Beauty Booking · تجربه‌ای تازه از زیبایی
            </footer>
          </div>
        </section>
      </div>
    </main>
  );
}