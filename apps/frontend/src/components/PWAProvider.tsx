"use client";

import { useEffect, useState } from "react";
import { SplashScreen } from "./SplashScreen";

/**
 * PWA Provider — handles service worker registration and splash screen.
 * Wraps children and shows splash on initial load.
 */
function shouldShowInstallSplash(): boolean {
  if (typeof window === "undefined") return false;
  try {
    return window.matchMedia("(display-mode: standalone)").matches;
  } catch {
    return false;
  }
}

export function PWAProvider({ children }: { children: React.ReactNode }) {
  const [showSplash, setShowSplash] = useState(false);
  const [appReady, setAppReady] = useState(false);

  // Service worker: registered by @ducanh2912/next-pwa at build time (see next.config.js).

  useEffect(() => {
    setShowSplash(shouldShowInstallSplash());
    const timer = setTimeout(() => setAppReady(true), 100);
    return () => clearTimeout(timer);
  }, []);

  return (
    <>
      {showSplash ? (
        <SplashScreen onComplete={() => setShowSplash(false)} />
      ) : null}
      <div
        style={{
          opacity: appReady && !showSplash ? 1 : 0,
          transition: "opacity 300ms ease",
        }}
      >
        {children}
      </div>
    </>
  );
}
