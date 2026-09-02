import type { Metadata, Viewport } from "next";
import "@fontsource-variable/source-serif-4";
import "@fontsource-variable/ibm-plex-sans";
import "@fontsource/ibm-plex-mono/400.css";
import "@fontsource/ibm-plex-mono/500.css";
import "./globals.css";

import { publicConfig } from "@/lib/config";

const title = "Payment Observatory — Payments intelligence case study";
const description =
  "An evidence-led case study of a deployable payments analytics system spanning transaction activity, merchant settlement, review outcomes, retention, and relational data design.";

export const metadata: Metadata = {
  metadataBase: new URL(publicConfig.siteUrl),
  title,
  description,
  applicationName: "Payment Observatory",
  authors: [{ name: "Abinash Prasana", url: publicConfig.repositoryUrl }],
  creator: "Abinash Prasana",
  category: "Data analytics",
  keywords: [
    "payment analytics",
    "SQL portfolio",
    "Streamlit dashboard",
    "PostgreSQL analytics",
    "financial data visualization",
  ],
  alternates: { canonical: "/" },
  openGraph: {
    type: "website",
    url: "/",
    siteName: "Payment Observatory",
    title,
    description,
    images: [{ url: "/opengraph-image", width: 1200, height: 630, alt: "Payment Observatory transaction reactor and case-study title" }],
  },
  twitter: {
    card: "summary_large_image",
    title,
    description,
    images: ["/opengraph-image"],
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
