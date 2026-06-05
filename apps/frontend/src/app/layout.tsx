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
import { MobileAppShell } from "@/components/MobileAppShell";
import { RouteTransitionShell } from "@/components/shared/RouteTransitionShell";
import { Toaster } from "@/components/shared/Toaster";
import { PlausibleAnalytics } from "@/components/PlausibleAnalytics";
import { MAIN_CONTENT_ID, SkipToContent } from "@/components/SkipToContent";
import { CommandPalette } from "@/components/CommandPalette";

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
      className={`dark ${inter.variable} ${crimsonPro.variable} ${jetbrainsMono.variable}`}
      suppressHydrationWarning
    >
      <head>
        <script
          dangerouslySetInnerHTML={{
            __html: `(function(){try{var t=localStorage.getItem('zed_cv_theme');if(t==='light'){document.documentElement.classList.remove('dark');}else{document.documentElement.classList.add('dark');}}catch(e){document.documentElement.classList.add('dark');}})();`,
          }}
        />
        <link rel="preconnect" href="https://api.zedapply.com" crossOrigin="anonymous" />
        <link
          rel="preconnect"
          href="https://chnesgmcuxyhwhzomdov.supabase.co"
          crossOrigin="anonymous"
        />
        <link rel="dns-prefetch" href="https://o4511365243076608.ingest.de.sentry.io" />
        <link rel="dns-prefetch" href="https://plausible.io" />
      </head>
      <body className="min-h-screen font-sans">
        <SkipToContent />
        <PlausibleAnalytics />
        <ThemeProvider>
          <ErrorBoundary>
            <AuthProvider>
              <SavedJobsProvider>
                <PWAProvider>
                  <MobileAppShell>
                    <OfflineBanner />
                    <Navbar />
                    <main id={MAIN_CONTENT_ID} tabIndex={-1} className="outline-none">
                      <RouteTransitionShell>{children}</RouteTransitionShell>
                    </main>
                  <PWAInstallPrompt />
                  <Footer />
                  <MobileTabBar />
                  <BwanaChatWidget />
                  <Toaster />
                  <CommandPalette />
                  </MobileAppShell>
                </PWAProvider>
              </SavedJobsProvider>
            </AuthProvider>
          </ErrorBoundary>
        </ThemeProvider>
      </body>
    </html>
  );
}
