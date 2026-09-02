import { expect, test, type Page } from "@playwright/test";

const caseStudyBaseURL =
  process.env.CASE_STUDY_BASE_URL ?? "http://127.0.0.1:3000";
const labBaseURL = process.env.LAB_BASE_URL ?? "http://127.0.0.1:8501";

async function expectNoHorizontalOverflow(page: Page) {
  const dimensions = await page.evaluate(() => ({
    clientWidth: document.documentElement.clientWidth,
    scrollWidth: document.documentElement.scrollWidth,
  }));
  expect(dimensions.scrollWidth).toBeLessThanOrEqual(dimensions.clientWidth + 1);
}

test.describe("editorial case study", () => {
  test("renders the full narrative and chapter navigation without overflow", async ({
    page,
  }) => {
    const hydrationWarnings: string[] = [];
    page.on("console", (message) => {
      if (
        message.type() === "error" &&
        /hydration|hydrated/i.test(message.text())
      ) {
        hydrationWarnings.push(message.text());
      }
    });

    await page.goto("/", { waitUntil: "domcontentloaded" });

    await expect(
      page.getByRole("heading", {
        level: 1,
        name: /Observe every link around 80,000 payment events/i,
      }),
    ).toBeVisible();

    const chapterNavigation = page.getByRole("navigation", {
      name: "Case study chapters",
    });
    await expect(chapterNavigation.getByRole("link")).toHaveCount(5);

    const labLink = page.getByRole("link", { name: /Open interactive lab/ }).first();
    await expect(labLink).toHaveAttribute("href", `${labBaseURL}/?view=overview`);

    await chapterNavigation.getByRole("link", { name: /Merchant flow/ }).click();
    await expect(page).toHaveURL(/#merchant-flow$/);
    await expect(page.locator("#merchant-flow")).toBeInViewport();

    await expectNoHorizontalOverflow(page);
    await page.waitForLoadState("load");
    expect(hydrationWarnings).toEqual([]);
  });

  test("keeps all evidence images real, dimensioned, and loadable", async ({ page }) => {
    await page.goto("/", { waitUntil: "domcontentloaded" });

    const images = page.locator("main img");
    const imageCount = await images.count();
    expect(imageCount).toBeGreaterThanOrEqual(8);

    for (let index = 0; index < imageCount; index += 1) {
      const image = images.nth(index);
      await image.scrollIntoViewIfNeeded();
      await expect
        .poll(
          () =>
            image.evaluate(
              (element) =>
                element instanceof HTMLImageElement &&
                element.complete &&
                element.naturalWidth > 0 &&
                element.width > 0 &&
                element.height > 0,
            ),
          { timeout: 15_000 },
        )
        .toBe(true);
    }
  });

  test("uses only locally served runtime assets", async ({ page }) => {
    const externalRuntimeRequests = new Set<string>();
    page.on("request", (request) => {
      const url = new URL(request.url());
      const target = new URL(caseStudyBaseURL);
      if (
        ["document", "script", "stylesheet", "font", "image"].includes(
          request.resourceType(),
        ) &&
        url.protocol !== "data:" &&
        url.protocol !== "blob:" &&
        url.origin !== target.origin
      ) {
        externalRuntimeRequests.add(request.url());
      }
    });

    await page.goto("/", { waitUntil: "networkidle" });
    expect([...externalRuntimeRequests]).toEqual([]);
  });

  test("honours reduced motion while keeping the flow control usable", async ({ page }) => {
    await page.emulateMedia({ reducedMotion: "reduce" });
    await page.goto("/", { waitUntil: "domcontentloaded" });

    expect(
      await page.evaluate(() =>
        window.matchMedia("(prefers-reduced-motion: reduce)").matches,
      ),
    ).toBe(true);

    const trace = page.locator(".trace-button");
    await expect(trace).toHaveText(/Trace a payment/);
    await trace.click();
    await expect(trace).toHaveText(/Tracing payment/);
    await expect(trace).toHaveText(/Replay trace/, { timeout: 2_000 });

    const transitionDuration = await trace.evaluate(
      (button) => getComputedStyle(button).transitionDuration,
    );
    const transitionMilliseconds = transitionDuration.endsWith("ms")
      ? Number.parseFloat(transitionDuration)
      : Number.parseFloat(transitionDuration) * 1_000;
    expect(transitionMilliseconds).toBeLessThanOrEqual(0.1);
  });
});
