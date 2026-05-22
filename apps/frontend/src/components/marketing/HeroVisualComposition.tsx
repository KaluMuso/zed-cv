"use client";

import { ApplyChannelsDetectedCard } from "@/components/marketing/ApplyChannelsDetectedCard";
import { HeroCvPreviewCard } from "@/components/marketing/HeroCvPreviewCard";
import { WhatsAppDigestCard } from "@/components/marketing/WhatsAppDigestCard";
import { FloatingCard } from "@/components/shared/FloatingCard";

/** Angled floating hero canvas: CV preview, WhatsApp digest, apply channels. */
export function HeroVisualComposition() {
  return (
    <div
      className="relative mx-auto flex min-h-[420px] w-full max-w-[440px] items-center justify-center sm:min-h-[460px] lg:mx-0 lg:max-w-none"
      aria-hidden={false}
    >
      <FloatingCard
        angle={-6}
        className="absolute left-0 top-6 z-0 sm:left-2 sm:top-4"
      >
        <HeroCvPreviewCard />
      </FloatingCard>

      <FloatingCard
        delay
        angle={3}
        className="relative z-10 ml-auto mt-2 sm:mr-0 sm:mt-0"
      >
        <WhatsAppDigestCard />
      </FloatingCard>

      <FloatingCard
        delay2
        angle={2}
        className="absolute bottom-0 right-0 z-20 sm:-bottom-2 sm:right-4"
      >
        <ApplyChannelsDetectedCard />
      </FloatingCard>
    </div>
  );
}
