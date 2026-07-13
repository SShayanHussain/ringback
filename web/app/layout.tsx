import "./globals.css";
import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Ringback — never miss a call, never miss a booking",
  description:
    "An inbound voice agent for home-services scheduling. Answers 24/7, books and reschedules, and hands off to a human when it should.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  // suppressHydrationWarning: browser extensions can inject DOM pre-hydration (PLAYBOOK §6).
  return (
    <html lang="en" suppressHydrationWarning>
      <body suppressHydrationWarning>{children}</body>
    </html>
  );
}
