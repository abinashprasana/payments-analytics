import type { MetadataRoute } from "next";

import { publicConfig } from "@/lib/config";

export const dynamic = "force-static";

export default function robots(): MetadataRoute.Robots {
  return {
    rules: { userAgent: "*", allow: "/" },
    sitemap: `${publicConfig.siteUrl}/sitemap.xml`,
    host: publicConfig.siteUrl,
  };
}
