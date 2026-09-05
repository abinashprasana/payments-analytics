import { expect, test, type Page } from "@playwright/test";

import projectData from "../src/data/project-data.json";

const caseStudyURL = (
  process.env.CASE_STUDY_BASE_URL ??
  "http://127.0.0.1:3000/payments-analytics"
).replace(/\/$/, "");

const expectedSections = [
  "question",
  "contract",
  "model",
  "baseline",
  "isolation",
  "classification",
  "recommendation",
  "validation",
  "workbench",
] as const;

async function openCaseStudy(page: Page) {
  await page.goto(caseStudyURL + "/", {
    waitUntil: "networkidle",
    timeout: 120_000,
  });
  await expect(
    page.getByRole("heading", { name: "The Settlement Gap", level: 1 }),
  ).toBeVisible();
}

async function expectNoPageOverflow(page: Page) {
  const width = await page.evaluate(() => ({
    client: document.documentElement.clientWidth,
    scroll: document.documentElement.scrollWidth,
  }));
  expect(width.scroll).toBeLessThanOrEqual(width.client + 1);
}

test.describe("authored settlement walkthrough", () => {
  test("keeps the nine-part investigation readable at the target width", async ({
    page,
  }) => {
    await openCaseStudy(page);

    await expect(page).toHaveTitle(/The Settlement Gap.*workbench that finds them/i);
    await expect(page.locator("h1")).toHaveCount(1);
    for (const sectionId of expectedSections) {
      await expect(page.locator("section#" + sectionId)).toBeAttached();
    }

    const navLabels = projectData.navigation.map(({ label }) => label);
    await expect(
      page.getByRole("navigation", { name: "Investigation chapters" }).getByRole("link"),
    ).toHaveText(navLabels);

    await expect(page.getByText(projectData.dataset.version, { exact: true }).first()).toBeVisible();
    await expect(page.getByText(projectData.build.commitSha, { exact: true }).first()).toBeVisible();
    await expect(
      page.getByText(projectData.question.conciseAnswer, { exact: true }).first(),
    ).toBeVisible();
    await expect(page.getByText("Synthetic demo snapshot", { exact: true }).first()).toBeVisible();

    const publicQueryIds = new Set([
      ...projectData.investigationSteps.map(({ queryId }) => queryId),
      projectData.trace.queryId,
      projectData.validation.explainQueryId,
    ]);
    for (const queryId of publicQueryIds) {
      await expect(page.locator("code", { hasText: queryId }).first()).toBeVisible();
    }

    await expect(page.locator('main img[src*="/media/"]')).toHaveCount(0);
    await expect(page.locator("body")).not.toContainText(/payment-observatory\.vercel\.app/i);
    await expectNoPageOverflow(page);
  });

  test("links one generated payment directly into the workbench", async ({ page }) => {
    await openCaseStudy(page);

    const traceLink = page.getByRole("link", { name: /Trace this payment/i });
    const href = await traceLink.getAttribute("href");
    expect(href).toBeTruthy();
    const target = new URL(href!);
    expect(target.searchParams.get("view")).toBe("trace");
    expect(target.searchParams.get("scenario")).toBe(projectData.trace.scenarioId);
    expect(target.searchParams.get("payment_id")).toBe(projectData.trace.paymentId);

    await expect(page.getByText(projectData.trace.paymentId, { exact: true }).first()).toBeVisible();
    await expect(page.getByText(/session-only/i).first()).toBeVisible();
    await expect(page.getByText(/wake after inactivity/i)).toBeVisible();
  });

  test("preserves keyboard navigation and reduced-motion behaviour", async ({
    page,
  }, testInfo) => {
    test.skip(testInfo.project.name !== "desktop-1440", "One interaction audit is sufficient.");
    await page.emulateMedia({ reducedMotion: "reduce" });
    await openCaseStudy(page);

    await page.keyboard.press("Home");
    await page.keyboard.press("Tab");
    const skipLink = page.getByRole("link", { name: "Skip to the walkthrough" });
    await expect(skipLink).toBeFocused();
    await skipLink.press("Enter");
    await expect(page).toHaveURL(/#main-content$/);

    const scrollBehaviour = await page.evaluate(
      () => getComputedStyle(document.documentElement).scrollBehavior,
    );
    expect(scrollBehaviour).toBe("auto");

    const firstChapter = page
      .getByRole("navigation", { name: "Investigation chapters" })
      .getByRole("link")
      .first();
    await firstChapter.focus();
    await expect(firstChapter).toBeFocused();

    const finalChapter = page
      .getByRole("navigation", { name: "Investigation chapters" })
      .getByRole("link", { name: "Workbench" });
    await finalChapter.click();
    await expect(page).toHaveURL(/#workbench$/);
    await expect(finalChapter).toHaveAttribute("aria-current", "location");
    const targetTop = await page.locator("section#workbench").evaluate(
      (section) => section.getBoundingClientRect().top,
    );
    expect(targetTop).toBeGreaterThanOrEqual(120);
    expect(targetTop).toBeLessThanOrEqual(145);

    await page.goto(caseStudyURL + "/#baseline", { waitUntil: "networkidle" });
    await expect(
      page
        .getByRole("navigation", { name: "Investigation chapters" })
        .getByRole("link", { name: "Baseline" }),
    ).toHaveAttribute("aria-current", "location");
  });

  test("loads only local page assets", async ({ page }, testInfo) => {
    test.skip(testInfo.project.name !== "desktop-1440", "One network audit is sufficient.");
    const externalAssets: string[] = [];
    const caseHost = new URL(caseStudyURL + "/").host;
    page.on("request", (request) => {
      const url = new URL(request.url());
      if (url.protocol.startsWith("http") && url.host !== caseHost) {
        externalAssets.push(request.url());
      }
    });

    await openCaseStudy(page);
    expect(externalAssets).toEqual([]);

    // Static export intentionally ships no React hydration runtime. The two
    // remaining scripts are authored inline behaviour and structured data.
    await expect(page.locator("script[src]")).toHaveCount(0);
    const structuredData = await page
      .locator('script[type="application/ld+json"]')
      .textContent();
    expect(() => JSON.parse(structuredData ?? "")).not.toThrow();
  });
});
