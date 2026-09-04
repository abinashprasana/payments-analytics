import rawProjectData from "@/data/project-data.json";

export interface Money {
  currency: string;
  minorUnits: number;
}

export interface DatasetMetadata {
  label: string;
  version: string;
  asOfDate: string;
  window: {
    firstTransactionDate: string;
    lastTransactionDate: string;
  };
  recordCounts: {
    sourceTables: number;
    transactions: number;
    eligiblePurchases: number;
    settlements: number;
  };
}

export interface NavigationItem {
  id: string;
  label: string;
}

export interface MetricDefinition {
  id: string;
  label: string;
  definition: string;
  population: string;
  grain: string;
  currencyBoundary: string;
  model: string;
  queryId: string;
  toleranceMinorUnits?: number;
}

export interface SourceEntity {
  name: string;
  grain: string;
  key: string;
  role: string;
}

export interface SourceRelationship {
  from: string;
  to: string;
  cardinality: string;
  note: string;
}

export interface Scenario {
  id: string;
  label: string;
  kind: string;
  date: string;
  currency: string;
  merchantCategory: string;
  expectedSignal: string;
  disclosure: string;
}

export interface InvestigationStep {
  id: string;
  label: string;
  question: string;
  queryId: string;
  model: string;
  sql: string;
  reading: string;
}

export interface DailyCloseRow {
  closeDate: string;
  analysisAsOfDate: string;
  currency: string;
  eligibleCount: number;
  matchedCount: number;
  coverageBps: number;
  overdueValue: Money;
  feeDelta: Money;
}

export interface SegmentFinding {
  merchantCategory: string;
  currency: string;
  eligibleCount: number;
  exceptionCount: number;
  exceptionRateBps: number;
  primaryReason: string;
  overdueValue: Money;
}

export interface ExceptionReason {
  id: string;
  label: string;
  count: number;
  affectedValue: Money;
}

export interface TraceEvidence {
  paymentId: string;
  scenarioId: string;
  transactionDate: string;
  merchantCategory: string;
  currency: string;
  status: string;
  gross: Money;
  applicableTerm: {
    validFrom: string;
    validTo: string | null;
    feeRateBps: number;
    settlementSlaDays: number;
  };
  expectedFee: Money;
  recordedFee: Money;
  expectedSettlementDate: string;
  recordedSettlementDate: string | null;
  flags: string[];
  primaryLabel: string;
  whyFlagged: string;
  queryId: string;
  model: string;
}

export interface QualityResult {
  checkId: string;
  label: string;
  status: "pass" | "warn" | "fail";
  checkedRows: number;
  detail: string;
}

export interface ModelDefinition {
  name: string;
  grain: string;
  purpose: string;
}

export interface WorkbenchView {
  id: string;
  label: string;
  purpose: string;
}

export interface CaseStudyDataV2 {
  schemaVersion: 2;
  dataset: DatasetMetadata;
  build: {
    commitSha: string;
    generatedAt: string;
    runtimeLabel: string;
  };
  navigation: NavigationItem[];
  question: {
    stakeholder: string;
    conciseAnswer: string;
    operationalDecision: string;
  };
  metricDefinitions: MetricDefinition[];
  sourceModel: {
    entities: SourceEntity[];
    relationships: SourceRelationship[];
  };
  scenarios: Scenario[];
  selectedScenarioId: string;
  investigationSteps: InvestigationStep[];
  dailyClose: DailyCloseRow[];
  segmentFindings: SegmentFinding[];
  exceptionSummary: ExceptionReason[];
  primaryLabelPrecedence: string[];
  trace: TraceEvidence;
  recommendation: {
    finding: string;
    action: string;
    owner: string;
    successMetricId: string;
  };
  validation: {
    explainModel: string;
    explainQueryId: string;
    explainSql: string;
    plan: string[];
    qualityResults: QualityResult[];
  };
  models: ModelDefinition[];
  limitations: string[];
  workbench: {
    views: WorkbenchView[];
    journey: string[];
    sleepDisclosure: string;
  };
  reproduction: {
    commands: string[];
    compatibilityEngines: string[];
  };
}

export const projectData = rawProjectData as CaseStudyDataV2;
