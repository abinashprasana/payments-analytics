const stripTrailingSlash = (value: string) => value.replace(/\/$/, "");

const normaliseBasePath = (value: string) => {
  const trimmed = stripTrailingSlash(value.trim());
  if (!trimmed) return "";
  return trimmed.startsWith("/") ? trimmed : `/${trimmed}`;
};

export const basePath = normaliseBasePath(
  process.env.NEXT_PUBLIC_BASE_PATH ?? "/payments-analytics",
);

export const publicConfig = {
  siteUrl: stripTrailingSlash(
    process.env.NEXT_PUBLIC_SITE_URL ??
      "https://abinashprasana.github.io/payments-analytics/",
  ),
  workbenchUrl: stripTrailingSlash(
    process.env.NEXT_PUBLIC_WORKBENCH_URL ??
      "https://abinashprasana-payments-analytics-dashboardapp-mrsz1m.streamlit.app/",
  ),
  // The Render service from render.yaml. Streamable HTTP endpoint, read-only.
  mcpUrl: stripTrailingSlash(
    process.env.NEXT_PUBLIC_MCP_URL ??
      "https://settlement-gap-mcp.onrender.com/mcp",
  ),
  repositoryUrl: stripTrailingSlash(
    process.env.NEXT_PUBLIC_REPOSITORY_URL ??
      "https://github.com/abinashprasana/payments-analytics",
  ),
} as const;

export const assetUrl = (path: string) =>
  `${basePath}${path.startsWith("/") ? path : `/${path}`}`;
