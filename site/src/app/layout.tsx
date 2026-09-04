import type { Metadata, Viewport } from "next";
import "@fontsource-variable/source-serif-4";
import "@fontsource-variable/ibm-plex-sans";
import "@fontsource/ibm-plex-mono/400.css";
import "@fontsource/ibm-plex-mono/500.css";
import "./globals.css";

import { publicConfig } from "@/lib/config";

const title = "The Settlement Gap — SQL reconciliation case study";
const description =
  "A reproducible SQL investigation into completed purchases that do not reconcile to recorded settlement value.";

export const metadata: Metadata = {
  metadataBase: new URL(publicConfig.siteUrl),
  title,
  description,
  applicationName: "The Settlement Gap",
  authors: [{ name: "Abinash Prasana", url: publicConfig.repositoryUrl }],
  creator: "Abinash Prasana",
  category: "Data analytics",
  keywords: [
    "payment analytics",
    "SQL portfolio",
    "settlement reconciliation",
    "Streamlit workbench",
    "PostgreSQL analytics",
    "financial data visualization",
  ],
  icons: {
    icon: [
      {
        url: `${publicConfig.siteUrl}/brand/payment-observatory-mark-mono.svg`,
        type: "image/svg+xml",
      },
    ],
  },
  alternates: { canonical: publicConfig.siteUrl },
  openGraph: {
    type: "website",
    url: publicConfig.siteUrl,
    siteName: "The Settlement Gap",
    title,
    description,
    images: [{ url: `${publicConfig.siteUrl}/opengraph-image`, width: 1200, height: 630, alt: "The Settlement Gap SQL reconciliation case study" }],
  },
  twitter: {
    card: "summary_large_image",
    title,
    description,
    images: [`${publicConfig.siteUrl}/opengraph-image`],
  },
};

export const viewport: Viewport = {
  colorScheme: "dark",
  themeColor: "#141C22",
  width: "device-width",
  initialScale: 1,
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body>
        <a className="skip-link" href="#main-content">Skip to case study</a>
        {children}
      </body>
    </html>
  );
}
