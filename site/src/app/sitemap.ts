import type { MetadataRoute } from "next";

import { publicConfig } from "@/lib/config";
import { projectData } from "@/lib/project-data";

export const dynamic = "force-static";

export default function sitemap(): MetadataRoute.Sitemap {
  return [
    {
      url: publicConfig.siteUrl,
      lastModified: new Date(projectData.build.generatedAt),
      changeFrequency: "monthly",
      priority: 1,
    },
  ];
}
