import type { Metadata, Viewport } from "next";
import "@fontsource-variable/source-serif-4";
import "@fontsource-variable/ibm-plex-sans";
import "@fontsource/ibm-plex-mono/400.css";
import "@fontsource/ibm-plex-mono/500.css";
import "./globals.css";

import { publicConfig } from "@/lib/config";

const title =
  "The Settlement Gap — why completed payments go unreconciled, and the workbench that finds them";
const description =
  "I traced why completed merchant purchases stop matching recorded settlement value, then built the workbench that does it live. Read the trace, then open the tool.";

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
    images: [{ url: `${publicConfig.siteUrl}/opengraph-image`, width: 1200, height: 630, alt: title }],
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
  themeColor: "#0B0E12",
  width: "device-width",
  initialScale: 1,
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body>
        <a className="skip-link" href="#main-content">Skip to the walkthrough</a>
        {children}
      </body>
    </html>
  );
}
