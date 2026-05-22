import type { Viewport } from "next";
import { Inter, Crimson_Pro, JetBrains_Mono } from "next/font/google";
import { siteDefaultMetadata } from "@/lib/site-metadata";
import "./globals.css";
import { Navbar } from "@/components/Navbar";
import { Footer } from "@/components/Footer";
import { MobileTabBar } from "@/components/MobileTabBar";
import { AuthProvider } from "@/lib/auth";
import { SavedJobsProvider } from "@/lib/SavedJobsProvider";
import { ThemeProvider } from "@/components/ThemeProvider";
import { ErrorBoundary } from "@/components/ErrorBoundary";
import { PWAProvider } from "@/components/PWAProvider";
import { OfflineBanner } from "@/components/shared/OfflineBanner";
import { PWAInstallPrompt } from "@/components/PWAInstallPrompt";
import { BwanaChatWidget } from "@/components/BwanaChatWidget";

const inter = Inter({
  subsets: ["latin"],
  display: "swap",
  variable: "--font-inter",
});

const crimsonPro = Crimson_Pro({
  weight: ["400", "600"],
  subsets: ["latin"],
  display: "swap",
  variable: "--font-crimson",
});

const jetbrainsMono = JetBrains_Mono({
  subsets: ["latin"],
  display: "swap",
  variable: "--font-jetbrains-mono",
});

export const viewport: Viewport = {
  themeColor: "#0E5C3A",
  width: "device-width",
  initialScale: 1,
  viewportFit: "cover",
};

export const metadata = siteDefaultMetadata;

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html
      lang="en"
      className={`${inter.variable} ${crimsonPro.variable} ${jetbrainsMono.variable}`}
      suppressHydrationWarning
    >
      <body
        className="min-h-screen"
        style={{ background: "var(--bg)", color: "var(--ink)" }}
      >
        <ThemeProvider>
          <ErrorBoundary>
            <AuthProvider>
              <SavedJobsProvider>
                <PWAProvider>
                  <OfflineBanner />
                  <Navbar />
                  {children}
                  <PWAInstallPrompt />
                  <Footer />
                  <MobileTabBar />
                  <BwanaChatWidget />
                </PWAProvider>
              </SavedJobsProvider>
            </AuthProvider>
          </ErrorBoundary>
        </ThemeProvider>
      </body>
    </html>
  );
}
