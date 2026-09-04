import { spawn } from "node:child_process";
import { existsSync } from "node:fs";
import { mkdir, writeFile } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

import { chromium } from "@playwright/test";
import { launch as launchChrome } from "chrome-launcher";
import lighthouse from "lighthouse";

import { assertLighthouseReport } from "./assert-lighthouse.mjs";

const scriptDirectory = path.dirname(fileURLToPath(import.meta.url));
const siteDirectory = path.resolve(scriptDirectory, "..");
const targetUrl =
  process.env.LIGHTHOUSE_URL ??
  process.env.CASE_STUDY_BASE_URL ??
  "http://127.0.0.1:3000/payments-analytics/";
const target = new URL(targetUrl);
const outputDirectory = path.join(siteDirectory, ".lighthouse");
const outputPath = path.join(outputDirectory, "report.json");
const chromeProfileDirectory = path.join(
  outputDirectory,
  `chrome-profile-${process.pid}`,
);
const useExistingServer = process.env.LIGHTHOUSE_USE_EXISTING_SERVER === "1";

async function waitForServer(url, timeoutMs = 60_000) {
  const deadline = Date.now() + timeoutMs;
  while (Date.now() < deadline) {
    try {
      const response = await fetch(url, { redirect: "follow" });
      if (response.ok) return;
    } catch {
      // The production server may still be binding its port.
    }
    await new Promise((resolve) => setTimeout(resolve, 500));
  }
  throw new Error(`Timed out waiting for ${url}`);
}

let siteProcess;
let chrome;

try {
  if (!useExistingServer) {
    const staticServer = path.join(siteDirectory, "scripts", "serve-static.mjs");
    siteProcess = spawn(
      process.execPath,
      [staticServer],
      {
        cwd: siteDirectory,
        env: {
          ...process.env,
          STATIC_HOST: target.hostname,
          STATIC_PORT: target.port || "3000",
        },
        stdio: ["ignore", "inherit", "inherit"],
      },
    );
  }

  await waitForServer(targetUrl);
  await mkdir(chromeProfileDirectory, { recursive: true });

  const playwrightChromium = chromium.executablePath();
  chrome = await launchChrome({
    chromePath:
      process.env.CHROME_PATH ||
      (existsSync(playwrightChromium) ? playwrightChromium : undefined),
    chromeFlags: [
      "--headless=new",
      "--no-sandbox",
      "--disable-dev-shm-usage",
      "--disable-gpu",
    ],
    // A caller-owned profile prevents chrome-launcher from recursively deleting
    // a still-locked Windows temp directory after an otherwise successful run.
    userDataDir: chromeProfileDirectory,
  });

  const runnerResult = await lighthouse(targetUrl, {
    port: chrome.port,
    logLevel: "info",
    output: "json",
    onlyCategories: ["performance", "accessibility"],
    formFactor: "mobile",
    screenEmulation: {
      mobile: true,
      width: 390,
      height: 844,
      deviceScaleFactor: 2,
      disabled: false,
    },
    throttlingMethod: "simulate",
  });

  if (!runnerResult?.lhr || !runnerResult.report) {
    throw new Error("Lighthouse did not return a report.");
  }

  await mkdir(outputDirectory, { recursive: true });
  await writeFile(
    outputPath,
    typeof runnerResult.report === "string"
      ? runnerResult.report
      : JSON.stringify(runnerResult.lhr),
  );

  const summary = assertLighthouseReport(runnerResult.lhr, targetUrl);
  console.log(`Lighthouse report: ${outputPath}`);
  console.log(JSON.stringify(summary, null, 2));
} finally {
  siteProcess?.kill("SIGTERM");
  // chrome-launcher uses `taskkill /T` on Windows, which can be denied inside
  // constrained local shells even though this process owns the browser. Kill
  // the direct child there; Linux CI keeps the launcher's process-tree cleanup.
  if (process.platform === "win32") {
    chrome?.process?.kill("SIGTERM");
  } else {
    chrome?.kill();
  }
}
