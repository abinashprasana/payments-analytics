import { publicConfig } from "@/lib/config";
import { projectData } from "@/lib/project-data";

export const selectedScenario = projectData.scenarios.find(
  (scenario) => scenario.id === projectData.selectedScenarioId,
)!;

export const baselineStep = projectData.investigationSteps.find(({ id }) => id === "baseline")!;
export const isolationStep = projectData.investigationSteps.find(({ id }) => id === "isolation")!;
export const classificationStep = projectData.investigationSteps.find(
  ({ id }) => id === "classification",
)!;

export const successMetric = projectData.metricDefinitions.find(
  ({ id }) => id === projectData.recommendation.successMetricId,
)!;

export const workbenchUrl = (() => {
  const params = new URLSearchParams({
    view: "trace",
    scenario: projectData.trace.scenarioId,
    payment_id: projectData.trace.paymentId,
  });
  return `${publicConfig.workbenchUrl}/?${params.toString()}`;
})();

export const structuredData = JSON.stringify({
  "@context": "https://schema.org",
  "@graph": [
    {
      "@type": "Article",
      headline: "The Settlement Gap",
      description: projectData.question.conciseAnswer,
      url: publicConfig.siteUrl,
      author: { "@type": "Person", name: "Abinash Prasana" },
      about: ["SQL", "payment settlement reconciliation", "data analytics"],
    },
    {
      "@type": "Dataset",
      name: projectData.dataset.label,
      version: projectData.dataset.version,
      temporalCoverage: `${projectData.dataset.window.firstTransactionDate}/${projectData.dataset.window.lastTransactionDate}`,
      description: selectedScenario.disclosure,
      distribution: {
        "@type": "DataDownload",
        encodingFormat: "text/csv",
        contentUrl: `${publicConfig.repositoryUrl}/tree/main/data/raw`,
      },
    },
  ],
}).replace(/</g, "\\u003c");
