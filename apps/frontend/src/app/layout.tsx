import type { Metadata, Viewport } from "next";
import { Inter, Instrument_Serif, JetBrains_Mono } from "next/font/google";
import "./globals.css";
import { Navbar } from "@/components/Navbar";
import { Footer } from "@/components/Footer";
import { MobileTabBar } from "@/components/MobileTabBar";
import { AuthProvider } from "@/lib/auth";
import { ThemeProvider } from "@/components/ThemeProvider";
import { ErrorBoundary } from "@/components/ErrorBoundary";
import { PWAProvider } from "@/components/PWAProvider";

const inter = Inter({
  subsets: ["latin"],
  display: "swap",
  variable: "--font-inter",
});

const instrumentSerif = Instrument_Serif({
  weight: "400",
  subsets: ["latin"],
  display: "swap",
  variable: "--font-instrument-serif",
  style: ["normal", "italic"],
});

const jetbrainsMono = JetBrains_Mono({
  subsets: ["latin"],
  display: "swap",
  variable: "--font-jetbrains-mono",
});

export const viewport: Viewport = {
  themeColor: "#0f5132",
  width: "device-width",
  initialScale: 1,
  viewportFit: "cover",
};

export const metadata: Metadata = {
  metadataBase: new URL("https://www.zedapply.com"),
  title: {
    default: "ZedApply — AI Job Matching for Zambia",
    template: "%s | ZedApply",
  },
  description:
    "Find jobs that match your skills. AI-powered matching, CV generation, and WhatsApp delivery for Zambian professionals.",
  keywords: [
    "Zambia jobs",
    "CV matching",
    "AI job matching",
    "Lusaka jobs",
    "Zambian careers",
    "CV builder Zambia",
    "job search Zambia",
  ],
  manifest: "/manifest.json",
  appleWebApp: {
    capable: true,
    statusBarStyle: "black-translucent",
    title: "ZedApply",
  },
  openGraph: {
    type: "website",
    locale: "en_ZM",
    url: "https://www.zedapply.com",
    siteName: "ZedApply",
    title: "ZedApply — AI Job Matching for Zambia",
    description:
      "Upload your CV and let AI score you against every open role in Zambia. Get matches on WhatsApp.",
    images: [{ url: "/og-image.png", width: 1200, height: 630, alt: "ZedApply" }],
  },
  twitter: {
    card: "summary_large_image",
    title: "ZedApply — AI Job Matching for Zambia",
    description:
      "Upload your CV and let AI score you against every open role in Zambia.",
  },
  robots: { index: true, follow: true },
  other: {
    "apple-mobile-web-app-capable": "yes",
  },
  icons: {
    icon: [
      { url: "/icons/icon-192.png", sizes: "192x192", type: "image/png" },
      { url: "/icons/icon-512.png", sizes: "512x512", type: "image/png" },
    ],
    apple: [{ url: "/icons/apple-touch-icon.png", sizes: "180x180" }],
  },
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html
      lang="en"
      className={`${inter.variable} ${instrumentSerif.variable} ${jetbrainsMono.variable}`}
      suppressHydrationWarning
    >
      <body
        className="min-h-screen"
        style={{ background: "var(--bg)", color: "var(--ink)" }}
      >
        <ThemeProvider>
          <ErrorBoundary>
            <AuthProvider>
              <PWAProvider>
                <Navbar />
                {children}
                <Footer />
                <MobileTabBar />
              </PWAProvider>
            </AuthProvider>
          </ErrorBoundary>
        </ThemeProvider>
      </body>
    </html>
  );
}
