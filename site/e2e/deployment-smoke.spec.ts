import { expect, test } from "@playwright/test";

const publicCaseStudyURL = process.env.PUBLIC_CASE_STUDY_URL?.replace(/\/$/, "");
const publicWorkbenchURL = process.env.PUBLIC_WORKBENCH_URL?.replace(/\/$/, "");
const expectedBuildSHA = process.env.EXPECTED_BUILD_SHA?.trim();

test.describe("public free-tier deployment", () => {
  test("serves matching Pages and Streamlit artifacts", async ({
    page,
    request,
  }, testInfo) => {
    test.skip(testInfo.project.name !== "desktop-1440", "One deployment probe is sufficient.");
    test.skip(
      !publicCaseStudyURL || !publicWorkbenchURL,
      "Set PUBLIC_CASE_STUDY_URL and PUBLIC_WORKBENCH_URL after deployment.",
    );
    const caseStudyURL = publicCaseStudyURL!;
    const workbenchURL = publicWorkbenchURL!;

    await page.goto(caseStudyURL + "/", {
      waitUntil: "networkidle",
      timeout: 120_000,
    });
    await expect(page).toHaveTitle(/The Settlement Gap.*workbench that finds them/i);
    await expect(
      page.getByRole("heading", { name: "The Settlement Gap", level: 1 }),
    ).toBeVisible();
    await expect(page.locator('link[rel="canonical"]')).toHaveAttribute(
      "href",
      caseStudyURL + "/",
    );

    const traceLink = page.getByRole("link", { name: /Trace this payment/i });
    await expect(traceLink).toHaveAttribute(
      "href",
      new RegExp(
        "^" +
          workbenchURL.replace(/[.*+?^\${}()|[\]\\]/g, "\\$&") +
          "/\\?view=trace&scenario=[^&]+&payment_id=.+",
      ),
    );
    expect((await page.content()).toLowerCase()).not.toContain(
      "payment-observatory.vercel.app",
    );

    if (expectedBuildSHA) {
      await expect(page.getByText(expectedBuildSHA, { exact: true }).first()).toBeVisible();
    }

    const health = await request.get(workbenchURL + "/_stcore/health", {
      timeout: 120_000,
    });
    expect(health.status()).toBeLessThan(500);

    await page.goto(workbenchURL + "/?view=catalog&scenario=normal", {
      waitUntil: "domcontentloaded",
      timeout: 120_000,
    });
    const ready = page.getByRole("heading", {
      name: "Find the close that did not close.",
      level: 1,
    });
    const sleeping = page.getByText(/app.*(?:sleep|hibernate)|wake.*app/i).first();
    await expect(ready.or(sleeping)).toBeVisible({ timeout: 120_000 });

    if (await sleeping.isVisible().catch(() => false)) {
      const wakeButton = page.getByRole("button", {
        name: /wake|get.*back up|run.*app/i,
      });
      if (await wakeButton.isVisible().catch(() => false)) {
        await wakeButton.click();
      }
      await expect(ready).toBeVisible({ timeout: 180_000 });
    }

    await expect(page.getByText("Metric and model catalog", { exact: true }).first()).toBeVisible({
      timeout: 120_000,
    });
    if (expectedBuildSHA) {
      await expect(
        page.getByText("Build " + expectedBuildSHA.slice(0, 8), { exact: true }).first(),
      ).toBeVisible();
    }
  });
});
