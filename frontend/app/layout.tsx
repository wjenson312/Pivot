import type { Metadata } from "next";
import ActiveRunBanner from "@/components/ActiveRunBanner";
import "./globals.css";

export const metadata: Metadata = {
  title: "Pivot Research Dashboard",
  description: "Transparent, reproducible analysis methods for the Pivot knee-loading wearable.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>
        <div className="app-shell">
          <header className="app-header">
            <div className="app-header__title">
              <span className="app-header__brand">Pivot</span>
              <span className="app-header__subtitle">Research Dashboard</span>
            </div>
            <p className="app-header__tagline">
              Every analysis method, in one place — the data, the science behind it, and how it was derived.
            </p>
          </header>
          <ActiveRunBanner />
          <main className="app-main">{children}</main>
        </div>
      </body>
    </html>
  );
}
