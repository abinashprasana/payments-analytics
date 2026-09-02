import rawProjectData from "@/data/project-data.json";

export interface DatasetWindow {
  firstTransactionDate: string;
  lastTransactionDate: string;
}

export interface RecordCounts {
  customers: number;
  accounts: number;
  merchants: number;
  transactions: number;
  settlements: number;
  fraudFlags: number;
  merchantlessTransactions: number;
}

export interface RelationshipEvidence {
  cardinality: string;
  description: string;
  linkedRecords: number;
}

export interface ProjectRelationships {
  customerToAccounts: RelationshipEvidence;
  accountToTransactions: RelationshipEvidence;
  transactionToMerchant: RelationshipEvidence;
  transactionToSettlement: RelationshipEvidence;
  transactionToFraudFlag: RelationshipEvidence;
}

export interface SettlementOutcome {
  status: string;
  count: number;
  share: number;
}

export interface ReviewOutcomes {
  total: number;
  resolved: number;
  unresolved: number;
  resolutionRate: number;
  flagRate: number;
}

export interface ProjectData {
  schemaVersion: number;
  datasetWindow: DatasetWindow;
  recordCounts: RecordCounts;
  relationships: ProjectRelationships;
  settlementOutcomes: SettlementOutcome[];
  reviewOutcomes: ReviewOutcomes;
  technology: string[];
  limitations: string[];
}

export const projectData = rawProjectData as ProjectData;
