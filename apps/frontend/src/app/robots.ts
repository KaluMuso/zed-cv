import type { MetadataRoute } from "next";

const BASE_URL =
  process.env.NEXT_PUBLIC_SITE_URL?.replace(/\/$/, "") ||
  "https://www.zedapply.com";

// robots.txt — explicitly blocks the authenticated/internal surfaces so
// crawlers don't index admin tools, signed-in profile views, or API
// responses (which would also waste crawl budget). The Sitemap entry
// points search engines at the dynamic sitemap.xml so they discover
// every active /jobs/[id] without depending on internal linking.
export default function robots(): MetadataRoute.Robots {
  return {
    rules: [
      {
        userAgent: "*",
        allow: "/",
        disallow: ["/admin/", "/profile/", "/auth/", "/api/"],
      },
    ],
    sitemap: `${BASE_URL}/sitemap.xml`,
    host: BASE_URL,
  };
}
