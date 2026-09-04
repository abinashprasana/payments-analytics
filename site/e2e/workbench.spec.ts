import { expect, test, type Page } from "@playwright/test";

const workbenchURL = (
  process.env.WORKBENCH_BASE_URL ?? "http://127.0.0.1:8501"
).replace(/\/$/, "");

const viewHeadings = {
  close: "Close health by currency",
  exceptions: "Exception queue",
  trace: "Payment trace",
  catalog: "Metric and model catalog",
} as const;

async function openWorkbench(
  page: Page,
  view: keyof typeof viewHeadings,
  scenario = "delayed_travel_gbp",
  paymentId?: string,
) {
  const params = new URLSearchParams({ view, scenario });
  if (paymentId) params.set("payment_id", paymentId);
  await page.goto(workbenchURL + "/?" + params.toString(), {
    waitUntil: "domcontentloaded",
    timeout: 120_000,
  });
  await expect(
    page.getByText(viewHeadings[view], { exact: true }).first(),
  ).toBeVisible({ timeout: 120_000 });
}

async function expectNoPageOverflow(page: Page) {
  const width = await page.evaluate(() => ({
    client: document.documentElement.clientWidth,
    scroll: document.documentElement.scrollWidth,
  }));
  expect(width.scroll).toBeLessThanOrEqual(width.client + 1);
}

test.describe("settlement operations workbench", () => {
  test("supports every stable deep link at the target width", async ({ page }) => {
    for (const view of Object.keys(viewHeadings) as Array<keyof typeof viewHeadings>) {
      await openWorkbench(page, view);
      const url = new URL(page.url());
      expect(url.searchParams.get("view")).toBe(view);
      expect(url.searchParams.get("scenario")).toBe("delayed_travel_gbp");
      await expect(page.getByText("Synthetic demo snapshot", { exact: true }).first()).toBeVisible();
      await expectNoPageOverflow(page);
    }
  });

  test("falls back to the normal close for unknown parameters", async ({
    page,
  }, testInfo) => {
    test.skip(testInfo.project.name !== "desktop-1440", "Desktop state contract.");
    await page.goto(workbenchURL + "/?view=unknown&scenario=unknown&payment_id=unknown", {
      waitUntil: "domcontentloaded",
      timeout: 120_000,
    });
    await expect(page.getByText(viewHeadings.close, { exact: true }).first()).toBeVisible({
      timeout: 120_000,
    });
    await expect
      .poll(() => {
        const url = new URL(page.url());
        return {
          view: url.searchParams.get("view"),
          scenario: url.searchParams.get("scenario"),
          payment: url.searchParams.get("payment_id"),
        };
      })
      .toEqual({ view: "close", scenario: "normal", payment: null });
  });

  test("changes scenario from the versioned selector", async ({ page }, testInfo) => {
    test.skip(testInfo.project.name !== "desktop-1440", "Desktop state contract.");
    await openWorkbench(page, "close", "normal");

    const scenarioSelect = page
      .locator('[data-testid="stSelectbox"]')
      .filter({ hasText: "Synthetic scenario" })
      .getByRole("combobox");
    await scenarioSelect.click();
    await page.getByText("Missing Retail / CAD batch", { exact: true }).last().click();

    await expect
      .poll(() => new URL(page.url()).searchParams.get("scenario"), { timeout: 60_000 })
      .toBe("missing_retail_cad");
    await expect(page.getByText(viewHeadings.close, { exact: true }).first()).toBeVisible();
  });

  test("filters, exports, traces, and resets session-only evidence", async ({
    page,
  }, testInfo) => {
    test.skip(testInfo.project.name !== "desktop-1440", "Desktop investigation journey.");
    await openWorkbench(page, "exceptions");

    const exportButton = page.getByRole("button", { name: "Export filtered evidence" });
    await expect(exportButton).toBeVisible();
    const downloadPromise = page.waitForEvent("download");
    await exportButton.click();
    const download = await downloadPromise;
    expect(download.suggestedFilename()).toMatch(/^settlement-exceptions-delayed_travel_gbp\.csv$/);

    const search = page.getByRole("textbox", { name: "Merchant or payment" });
    await search.fill("__no_matching_payment__");
    await search.press("Enter");
    await expect(
      page.getByText("No queue rows match the display filters. Clear them to continue.", {
        exact: true,
      }),
    ).toBeVisible();
    await search.clear();
    await search.press("Enter");
    await expect(page.getByRole("button", { name: "Open payment trace" })).toBeVisible();

    await page.getByRole("button", { name: "Open payment trace" }).click();
    await expect(page.getByText(viewHeadings.trace, { exact: true }).first()).toBeVisible();
    await expect
      .poll(() => {
        const url = new URL(page.url());
        return Boolean(
          url.searchParams.get("payment_id") &&
          url.searchParams.get("view") === "trace",
        );
      })
      .toBe(true);

    const note = page.getByRole("textbox", { name: "Session note" });
    await note.fill("Checked SQL lineage in browser test.");
    await page.getByRole("button", { name: "Save session note" }).click();
    await expect(page.getByText("Saved for this session only.", { exact: true })).toBeVisible();

    await page.getByRole("button", { name: "Reset session-only reviews" }).click();
    await expect(page.getByText("Session review state cleared.", { exact: true })).toBeVisible();
    await expect(page.getByRole("textbox", { name: "Session note" })).toHaveValue("");
  });
});
