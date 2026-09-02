const stripTrailingSlash = (value: string) => value.replace(/\/$/, "");

export const publicConfig = {
  siteUrl: stripTrailingSlash(
    process.env.NEXT_PUBLIC_SITE_URL ?? "https://payment-observatory.vercel.app/",
  ),
  labUrl: stripTrailingSlash(
    process.env.NEXT_PUBLIC_LAB_URL ??
      "https://abinashprasana-payments-analytics-dashboardapp-mrsz1m.streamlit.app/",
  ),
  repositoryUrl: stripTrailingSlash(
    process.env.NEXT_PUBLIC_REPOSITORY_URL ??
      "https://github.com/abinashprasana/payments-analytics",
  ),
} as const;
