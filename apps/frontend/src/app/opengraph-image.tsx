import { ImageResponse } from "next/og";
import { buildSiteOgImageElement, OG_IMAGE_SIZE } from "@/lib/og-image-builder";

export const runtime = "edge";

export const alt = "ZedApply — AI job matching for Zambia";
export const size = OG_IMAGE_SIZE;
export const contentType = "image/png";

export default function OgImage() {
  return new ImageResponse(buildSiteOgImageElement(), { ...size });
}
