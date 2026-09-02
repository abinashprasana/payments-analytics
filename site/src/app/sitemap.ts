import type { MetadataRoute } from "next";

import { publicConfig } from "@/lib/config";

export default function sitemap(): MetadataRoute.Sitemap {
  return [
    {
      url: publicConfig.siteUrl,
      lastModified: new Date("2026-08-31T00:00:00.000Z"),
      changeFrequency: "monthly",
      priority: 1,
    },
  ];
}
