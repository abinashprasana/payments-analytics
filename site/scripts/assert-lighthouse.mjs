const MINIMUM_SCORE = 0.9;
const MAXIMUM_LCP_MS = 2_500;
const MAXIMUM_CLS = 0.1;

function auditValue(report, auditId) {
  const value = report.audits?.[auditId]?.numericValue;
  return typeof value === "number" ? value : Number.NaN;
}

export function assertLighthouseReport(report, targetUrl) {
  const performance = report.categories?.performance?.score;
  const accessibility = report.categories?.accessibility?.score;
  const lcp = auditValue(report, "largest-contentful-paint");
  const cls = auditValue(report, "cumulative-layout-shift");
  const failures = [];

  if (typeof performance !== "number" || performance < MINIMUM_SCORE) {
    failures.push(`performance ${(performance ?? 0) * 100}% is below 90%`);
  }
  if (typeof accessibility !== "number" || accessibility < MINIMUM_SCORE) {
    failures.push(`accessibility ${(accessibility ?? 0) * 100}% is below 90%`);
  }
  if (!Number.isFinite(lcp) || lcp > MAXIMUM_LCP_MS) {
    failures.push(`LCP ${Math.round(lcp)}ms exceeds 2500ms`);
  }
  if (!Number.isFinite(cls) || cls > MAXIMUM_CLS) {
    failures.push(`CLS ${cls} exceeds 0.1`);
  }

  const targetOrigin = new URL(targetUrl).origin;
  const runtimeTypes = new Set(["Script", "Stylesheet", "Font"]);
  const externalRuntimeRequests = (
    report.audits?.["network-requests"]?.details?.items ?? []
  ).filter((item) => {
    if (!item?.url || !runtimeTypes.has(item.resourceType)) return false;
    const requestUrl = new URL(item.url);
    return !["data:", "blob:"].includes(requestUrl.protocol) && requestUrl.origin !== targetOrigin;
  });
  if (externalRuntimeRequests.length > 0) {
    failures.push(
      `external runtime requests detected: ${externalRuntimeRequests
        .map((item) => item.url)
        .join(", ")}`,
    );
  }

  const summary = {
    performance: Math.round((performance ?? 0) * 100),
    accessibility: Math.round((accessibility ?? 0) * 100),
    lcpMs: Math.round(lcp),
    cls: Number(cls.toFixed(4)),
    externalRuntimeRequests: externalRuntimeRequests.length,
  };

  if (failures.length > 0) {
    throw new Error(`Lighthouse budget failed:\n- ${failures.join("\n- ")}`);
  }

  return summary;
}
