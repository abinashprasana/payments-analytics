import { expect, test, type Page } from "@playwright/test";

const caseStudyBaseURL =
  process.env.CASE_STUDY_BASE_URL ?? "http://127.0.0.1:3000";
const labBaseURL = process.env.LAB_BASE_URL ?? "http://127.0.0.1:8501";

const viewHeadings = {
  overview: "Read the payment system in one pass",
  merchant: "Track merchant value through settlement",
  risk: "See what entered review and what cleared",
  retention: "Read customer return patterns without filling the future",
  model: "Trace the data before reading the metrics",
} as const;

async function openLab(page: Page, view: string) {
  await page.goto(`${labBaseURL}/?view=${view}`, {
    waitUntil: "domcontentloaded",
    timeout: 120_000,
  });
  const expected =
    view in viewHeadings
      ? viewHeadings[view as keyof typeof viewHeadings]
      : viewHeadings.overview;
  await expect(page.getByText(expected, { exact: true })).toBeVisible({
    timeout: 120_000,
  });
}

async function expectNoHorizontalOverflow(page: Page) {
  const dimensions = await page.evaluate(() => ({
    clientWidth: document.documentElement.clientWidth,
    scrollWidth: document.documentElement.scrollWidth,
  }));
  expect(dimensions.scrollWidth).toBeLessThanOrEqual(dimensions.clientWidth + 1);
}

test.describe("interactive analytical lab", () => {
  test("loads the CSV fallback, cross-link, navigation, and one WebGL surface", async ({
    page,
  }) => {
    await openLab(page, "overview");

    await expect(page.getByText("Repository CSV snapshot", { exact: true }).first()).toBeVisible();
    await expect(page.getByRole("link", { name: "Read case study" })).toHaveAttribute(
      "href",
      caseStudyBaseURL,
    );

    for (const label of [
      "Overview",
      "Merchant flow",
      "Risk monitor",
      "Retention",
      "Data model",
    ]) {
      await expect(page.getByRole("button", { name: new RegExp(label) })).toBeVisible();
    }

    const canvasCount = await page.locator("canvas").count();
    expect(canvasCount).toBeLessThanOrEqual(1);
    await expectNoHorizontalOverflow(page);
  });

  test("falls back from an unknown deep link", async ({ page }) => {
    await openLab(page, "unknown");
    await expect(page).toHaveURL(/\?view=overview$/);
  });

  test("honours reduced motion in the custom analytical controls", async ({ page }) => {
    await page.emulateMedia({ reducedMotion: "reduce" });
    await openLab(page, "overview");

    const riskButton = page.getByRole("button", { name: /Risk monitor/ });
    const transitionDuration = await riskButton.evaluate(
      (button) => getComputedStyle(button).transitionDuration,
    );
    const transitionMilliseconds = transitionDuration.endsWith("ms")
      ? Number.parseFloat(transitionDuration)
      : Number.parseFloat(transitionDuration) * 1_000;
    expect(transitionMilliseconds).toBeLessThanOrEqual(0.1);
  });

  test("supports every deep link and keeps navigation in sync", async ({
    page,
  }, testInfo) => {
    test.skip(testInfo.project.name !== "desktop-1440", "Desktop interaction contract");

    for (const [view, heading] of Object.entries(viewHeadings)) {
      await openLab(page, view);
      await expect(page.getByText(heading, { exact: true })).toBeVisible();
      await expect(page).toHaveURL(new RegExp(`\\?view=${view}$`));
    }

    await openLab(page, "overview");
    await page.getByRole("button", { name: /Risk monitor/ }).click();
    await expect(page).toHaveURL(/\?view=risk$/);
    await expect(page.getByText(viewHeadings.risk, { exact: true })).toBeVisible();
  });

  test("applies previous-period scope and recovers from an empty state", async ({
    page,
  }, testInfo) => {
    test.skip(testInfo.project.name !== "desktop-1440", "Desktop interaction contract");
    await openLab(page, "overview");

    await page.getByRole("button", { name: /Adjust scope/ }).click();
    await page.locator("#date-start").fill("2024-01-01");
    await page.locator("#compare-previous").check({ force: true });
    await page.getByRole("button", { name: /Apply scope/ }).click();

    await expect(page.getByText("Previous period", { exact: true }).first()).toBeVisible();
    await expect(page.getByText(/Showing [\d,]+ of 80,000 transactions/)).toBeVisible();

    await page.getByRole("button", { name: /Adjust scope/ }).click();
    const currencies = page.locator('input[name="currency"]');
    const currencyCount = await currencies.count();
    for (let index = 0; index < currencyCount; index += 1) {
      await currencies.nth(index).uncheck({ force: true });
    }
    await page.getByRole("button", { name: /Apply scope/ }).click();

    await expect(page.getByText("No records match these filters.", { exact: true })).toBeVisible();
    await page.getByRole("button", { name: "Reset filters" }).click();
    await expect(page.getByText(viewHeadings.overview, { exact: true })).toBeVisible();
    await expect(page.getByText(/Showing 80,000 of 80,000 transactions/)).toBeVisible();
  });

  test("exposes semantic table alternatives for graphical analysis", async ({
    page,
  }, testInfo) => {
    test.skip(testInfo.project.name !== "desktop-1440", "Desktop interaction contract");

    await openLab(page, "risk");
    await page.getByText("Open review-flow data table", { exact: true }).click();
    const reviewTable = page.locator("table").first();
    await expect(reviewTable).toBeVisible();
    await expect(reviewTable.getByRole("columnheader", { name: "Flag reason" })).toBeVisible();
    await expect(reviewTable.getByRole("columnheader", { name: "Review outcome" })).toBeVisible();

    await openLab(page, "retention");
    await page.getByText("Open retention data table", { exact: true }).click();
    const retentionTable = page.locator("table").first();
    await expect(retentionTable).toBeVisible({ timeout: 60_000 });
    await expect(
      retentionTable.getByRole("columnheader", { name: "Joining cohort" }),
    ).toBeVisible();
  });
});
