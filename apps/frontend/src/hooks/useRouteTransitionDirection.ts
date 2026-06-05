"use client";

import { useEffect, useRef, useState } from "react";
import { usePathname } from "next/navigation";
import {
  getRouteTransitionVariant,
  type RouteTransitionVariant,
} from "@/lib/mobile-transitions";

export function useRouteTransitionDirection(): RouteTransitionVariant {
  const pathname = usePathname();
  const prevRef = useRef(pathname);
  const [variant, setVariant] = useState<RouteTransitionVariant>("fade");

  useEffect(() => {
    const prev = prevRef.current;
    if (prev !== pathname) {
      setVariant(getRouteTransitionVariant(prev, pathname));
      prevRef.current = pathname;
    }
  }, [pathname]);

  return variant;
}
