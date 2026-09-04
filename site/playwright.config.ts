import { defineConfig } from "@playwright/test";

const caseStudyBaseURL = `${
  process.env.CASE_STUDY_BASE_URL ??
  "http://127.0.0.1:3000/payments-analytics"
}`.replace(/\/$/, "");
const caseStudyPageURL = `${caseStudyBaseURL}/`;
const workbenchBaseURL = process.env.WORKBENCH_BASE_URL ?? "http://127.0.0.1:8501";
const pythonExecutable = process.env.PYTHON_EXECUTABLE ?? "python";
const reuseExistingServer = process.env.CI !== "true";
const skipLocalServers =
  process.env.PUBLIC_DEPLOYMENT === "1" ||
  process.env.PLAYWRIGHT_SKIP_LOCAL_SERVERS === "1";

const viewports = [
  { name: "desktop-1440", width: 1440, height: 900 },
  { name: "desktop-1024", width: 1024, height: 900 },
  { name: "tablet-768", width: 768, height: 900 },
  { name: "mobile-390", width: 390, height: 844 },
] as const;

export default defineConfig({
  testDir: "./e2e",
  fullyParallel: false,
  forbidOnly: Boolean(process.env.CI),
  retries: process.env.CI ? 1 : 0,
  workers: process.env.CI ? 1 : undefined,
  timeout: 120_000,
  expect: {
    timeout: 30_000,
  },
  reporter: process.env.CI
    ? [["line"], ["html", { open: "never" }]]
    : [["list"], ["html", { open: "never" }]],
  outputDir: "test-results",
  use: {
    baseURL: caseStudyPageURL,
    browserName: "chromium",
    colorScheme: "light",
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
    video: "retain-on-failure",
  },
  projects: viewports.map(({ name, width, height }) => ({
    name,
    use: { viewport: { width, height } },
  })),
  webServer: skipLocalServers ? undefined : [
    {
      command: "npm run serve:static",
      url: caseStudyPageURL,
      timeout: 180_000,
      reuseExistingServer,
      stdout: "pipe",
      stderr: "pipe",
    },
    {
      command:
        `"${pythonExecutable}" -m streamlit run ../dashboard/app.py --server.address 127.0.0.1 --server.port 8501 --server.headless true --server.fileWatcherType none`,
      url: `${workbenchBaseURL}/?view=close&scenario=normal`,
      timeout: 180_000,
      reuseExistingServer,
      stdout: "pipe",
      stderr: "pipe",
      env: {
        ...process.env,
        CASE_STUDY_URL: caseStudyBaseURL,
        DB_HOST: "127.0.0.1",
        DB_PORT: "1",
        DB_CONNECT_TIMEOUT: "1",
      },
    },
  ],
});
