import type { Metadata } from "next";
import "@fontsource-variable/vazirmatn";
import "./globals.css";

export const metadata: Metadata = {
  title: "Beauty Booking | رزرو خدمات زیبایی",
  description:
    "فضایی مدرن برای رزرو و مدیریت خدمات زیبایی، سالن‌ها و متخصصان.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="fa" dir="rtl">
      <body>{children}</body>
    </html>
  );
}