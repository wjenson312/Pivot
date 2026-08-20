import type { Metadata } from "next";
import { Inter } from "next/font/google";
import ActiveRunBanner from "@/components/ActiveRunBanner";
import AppDock from "@/components/AppDock";
import "./globals.css";

const inter = Inter({ subsets: ["latin"], variable: "--font-inter" });

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
    <html lang="en" className={inter.variable}>
      <body>
        <div className="app-shell">
          <header className="app-header">
            <div className="app-header__title">
              <span className="app-header__mark" aria-hidden="true" />
              <span className="app-header__brand">Pivot</span>
              <span className="app-header__subtitle">Research Dashboard</span>
            </div>
            <p className="app-header__tagline">
              Every analysis method, in one place — the data, the science behind it, and how it was derived.
            </p>
          </header>
          <ActiveRunBanner />
          <main className="app-main">{children}</main>
          <AppDock />
        </div>
      </body>
    </html>
  );
}
