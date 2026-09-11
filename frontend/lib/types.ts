/** Shared TypeScript types mirroring the backend API contract. */

export type ApplicationStatus =
  | "draft"
  | "documents_pending"
  | "underwriting"
  | "awaiting_human"
  | "decision_pending"
  | "approved"
  | "declined"
  | "referred"
  | "cancelled";

export interface ProductRequest {
  type: string;
  amount: number;
  tenure_months: number;
  rate_annual: number;
}

export interface BorrowerView {
  ref_id: string;
  age: number;
  location_tier: string;
  full_name?: string | null;
  declared_monthly_income?: number | null;
  employment_type?: string | null;
}

export interface LoanRequest {
  amount: number;
  tenure_months: number;
  vehicle_price?: number | null;
  down_payment?: number | null;
}

export interface Application {
  id: string;
  status: ApplicationStatus;
  product: ProductRequest;
  borrower: BorrowerView;
  loan_request: LoanRequest;
  latest_run_id?: string | null;
  latest_decision?: string | null;
  created_at?: string;
  updated_at?: string;
}

export interface CreateApplicationPayload {
  product: ProductRequest;
  borrower: BorrowerView;
  loan_request: LoanRequest;
}

// ---- Auth ----

export interface AuthUser {
  email: string;
  name: string;
  role: string;
}

export interface LoginResponse {
  access_token: string;
  token_type: "bearer";
  user: AuthUser;
}

// ---- Documents ----

export type DocumentCategory =
  | "kyc"
  | "bank_statement"
  | "dealer_invoice"
  | "platform_earnings"
  | "other";

export interface Document {
  id: string;
  application_id: string;
  file_name: string;
  category: string | null;
  storage_key: string;
  content_type: string | null;
  size_bytes: number;
  uploaded_at: string | null;
  text_preview?: string | null;
}

// ---- Underwriting ----

export type PolicyProfile = "default" | "conservative" | "aggressive";

export interface UnderwriteResponse {
  run_id: string;
  application_id: string;
  status: string;
}

export type ReasonSeverity = "info" | "warning" | "blocker";

export interface Reason {
  code: string;
  severity: ReasonSeverity;
  message?: string;
  field?: string;
}

/** Backwards-compatible alias used by older scaffold code. */
export type DecisionReason = Reason;

export type ReviewStatus = "auto" | "accepted" | "corrected" | "rejected";

export interface EvidenceItem {
  field: string;
  value: string | number | null | number[];
  confidence: number;
  source_document: string | null;
  page: number | null;
  evidence: string | null;
  kind?: string;
  review_status?: ReviewStatus;
}

export type ReconciliationSeverity = "LOW" | "MEDIUM" | "HIGH";

export interface ReconciliationItem {
  type: string;
  severity: ReconciliationSeverity;
  description: string;
  documents: string[];
  evidence: string[];
  impact: string;
  mismatch_percentage?: number;
}

export interface Reconciliation {
  items: ReconciliationItem[];
  income_mismatch_percentage: number | null;
}

export interface Financials {
  emi: number;
  foir: number;
  ltv: number;
  existing_obligations: number;
  verified_income: number;
  income_stability: number;
  income_volatility: number;
  loan_to_income: number;
  emi_to_income: number;
  down_payment: number;
  calculation_inputs: Record<string, unknown>;
  formula_version: string;
  // contract aliases also present
  monthly_income: number;
  total_monthly_obligations: number;
  monthly_emi: number;
}

export type RiskBand = "LOW" | "MEDIUM" | "HIGH";

export interface ShapContribution {
  feature: string;
  label: string;
  value: number;
  value_display: string;
  baseline: number;
  baseline_display: string;
  /** Shapley value φ: contribution to the risk score relative to the baseline borrower. */
  shap: number;
  direction: "raises" | "lowers" | "neutral";
  /** Share of total |φ| mass, 0..1. */
  share: number;
}

export interface ShapExplanation {
  /** "tree_shap" | "xgboost_pred_contribs" | "additive_exact" */
  method: string;
  base_value: number;
  score: number;
  sum_contributions: number;
  additivity_error: number;
  contributions: ShapContribution[];
  top_risk_raising: string[];
  top_risk_lowering: string[];
  baseline_description?: string;
}

export interface Risk {
  risk_score: number;
  risk_band: RiskBand;
  model_version: string;
  model_backend: string;
  features?: Record<string, number>;
  shap?: ShapExplanation | null;
}

export interface PolicyCheck {
  check: string;
  code: string;
  value: number;
  limit: number;
  comparator: string;
  margin: number;
  passed: boolean;
  display: string;
}

/** Why this outcome for this person — policy margins (the cause) + SHAP drivers (the context). */
export interface DecisionExplanation {
  outcome: string;
  headline: string;
  sentences: string[];
  plain_text: string;
  policy_checks: PolicyCheck[];
  reason_codes: string[];
  shap_summary: {
    method: string | null;
    base_value: number | null;
    score: number | null;
    top_risk_raising: ShapContribution[];
    top_risk_lowering: ShapContribution[];
  };
  math_lines: string[];
  generated_by: string;
  llm_error?: string | null;
}

export interface RiskReasoning {
  risk_level: string;
  strengths: string[];
  risks: string[];
  uncertainties: string[];
  reasoning: string[];
  evidence_refs: string[];
}

export interface LowConfidenceField {
  field: string;
  confidence: number;
  threshold: number;
  requires_human_review: boolean;
  source_document?: string | null;
  evidence?: string | null;
  /** Value and page of the weakest evidence item for this field (the one being reviewed). */
  value?: unknown;
  page?: number | null;
}

export type ReviewAction = "accept" | "correct" | "reject" | "override";

export interface HumanReview {
  id: string;
  field: string;
  original_value: unknown;
  corrected_value: unknown;
  action: ReviewAction;
  reviewer: string | null;
  note: string | null;
  timestamp: string;
}

export type NodeStatusValue = "pending" | "ok" | "paused" | "error" | "skipped";

export interface NodeStatus {
  name: string;
  status: NodeStatusValue;
  duration_ms?: number;
  detail?: Record<string, unknown>;
}

export type RunStatus = "created" | "running" | "awaiting_human" | "completed" | "failed";

export type Decision = "approved" | "declined" | "referred" | "human_review";

export interface DecisionSummary {
  decision: Decision | string | null;
  confidence: number | null;
  reasons: Reason[];
}

export interface PolicyInfo {
  profile: string;
  version: string;
  config?: Record<string, unknown>;
}

export interface RunState {
  run_id: string;
  application_id: string | null;
  status: RunStatus;
  decision: Decision | null;
  confidence: number | null;
  reasons: Reason[];
  financials: Financials | null;
  risk: Risk | null;
  risk_reasoning: RiskReasoning | null;
  evidence: EvidenceItem[];
  reconciliation: Reconciliation;
  confidence_summary: { per_field: Record<string, number>; overall: number };
  low_confidence: LowConfidenceField[];
  human_reviews: HumanReview[];
  review_questions: string[];
  policy: PolicyInfo;
  nodes: NodeStatus[];
  memo?: CreditMemo | null;
  /** Automatic what-if computed for declined runs: the smallest change that approves. */
  approval_path?: WhatIfMinChange | null;
  /** SHAP + policy-margin explanation of the outcome, in numbers and words. */
  explanation?: DecisionExplanation | null;
  /** Backend-relative URL of the auto-generated credit memo PDF (null until the run completes). */
  memo_pdf_url?: string | null;
  created_at?: string;
  updated_at?: string;
  error?: string | null;
  /** Present on a resume response that is still awaiting human input. */
  pending_fields?: string[];
}

/** Backwards-compatible alias used by older scaffold code. */
export type UnderwritingDecision = RunState;

export const NODE_ORDER = [
  "classification",
  "extraction",
  "confidence_validation",
  "reconciliation",
  "deterministic_compute",
  "xgboost_risk",
  "risk_reasoning",
  "decision_policy",
  "explanation",
  "audit",
] as const;

// ---- Resume ----

export interface FieldReviewInput {
  field: string;
  action: "accept" | "correct" | "reject";
  corrected_value?: unknown;
  note?: string;
}

export interface ResumePayload {
  reviewer: string;
  reviews: FieldReviewInput[];
  decision_override?: { decision: "approved" | "declined" | "referred"; note?: string };
}

// ---- Trace / replay ----

export interface TraceStep {
  sequence: number;
  agent: string;
  event_type: string;
  timestamp: string;
  payload: Record<string, unknown>;
}

export interface TraceResponse {
  run_id: string;
  status: string;
  nodes: NodeStatus[];
  steps: TraceStep[];
}

export interface ReplaySnapshot {
  financials: Financials | null;
  risk: Risk | null;
  decision: DecisionSummary | string | null;
}

export interface ReplayDiff {
  field: string;
  original: unknown;
  replayed: unknown;
  equal: boolean;
}

export interface ReplayResponse {
  run_id: string;
  policy: { profile: string; version: string };
  original: ReplaySnapshot;
  replayed: ReplaySnapshot;
  diffs: ReplayDiff[];
  deterministic: boolean;
  replayed_at: string;
}

// ---- What-if ----

export interface WhatIfOverrides {
  loan_amount?: number;
  tenure_months?: number;
  annual_rate?: number;
  vehicle_price?: number;
  existing_monthly_obligations?: number;
  monthly_income?: number;
  down_payment?: number;
}

export interface WhatIfRequest {
  overrides: WhatIfOverrides;
  policy_profile?: string;
  find_min_change?: boolean;
}

export interface WhatIfMinChange {
  changes: Record<string, number>;
  financials: Financials | null;
  decision: { decision: string; reasons: Reason[] };
  description: string;
}

export interface WhatIfResponse {
  what_if_id: string;
  run_id: string;
  immutable: true;
  base: { financials: Financials | null; decision: DecisionSummary };
  scenario: {
    overrides: WhatIfOverrides;
    financials: Financials | null;
    risk: Risk | null;
    decision: DecisionSummary;
  };
  min_change_for_approval: WhatIfMinChange | null;
}

// ---- Credit memo ----

/** Narrative written from verified numbers only — by Gemini when a key is configured, else a template. */
export interface MemoNarrative {
  executive_summary: string;
  borrower_explanation: string;
  key_drivers: string[];
  next_steps: string[];
  /** "template" or "<provider>:<model>", e.g. "gemini:gemini-2.0-flash". */
  generated_by: string;
  numbers_source?: string;
  llm_error?: string | null;
}

export interface CreditMemo {
  run_id: string;
  application_id: string;
  title: string;
  generated_at: string;
  /** True once the backend has rendered and cached the PDF. */
  pdf_ready?: boolean;
  /** Backend-relative URL of the cached PDF. */
  pdf_url?: string;
  sections: {
    narrative?: MemoNarrative | null;
    approval_path?: WhatIfMinChange | null;
    decision_explanation?: DecisionExplanation | null;
    borrower_summary: Record<string, unknown>;
    extracted_facts: EvidenceItem[];
    calculated_values: Financials | null;
    risk_signal: Risk | null;
    ai_reasoning: RiskReasoning | null;
    policy_rules: Record<string, unknown>;
    human_overrides: HumanReview[];
    decision: DecisionSummary;
    reason_codes: string[];
  };
  generated_by: string;
}

// ---- Dashboard / audit ----

export interface RunSummary {
  run_id: string;
  application_id: string;
  status: string;
  decision: string | null;
  created_at: string;
}

export interface HealthResponse {
  status: string;
  service: string;
  mock_ai_mode: boolean;
  ai_service_url?: string;
  ai_service?: {
    status: string;
    mock_ai_mode?: boolean;
    policy_profile?: string;
    risk_backend?: string;
    graph_backend?: string;
    llm_provider?: string;
    llm_model?: string | null;
    error?: string;
  };
}

// ---- Risk model evaluation (XGBoost / fallback) ----

export interface RiskConfusionMatrix {
  tn: number;
  fp: number;
  fn: number;
  tp: number;
  matrix: number[][];
}

export interface RocPoint {
  threshold: number;
  tpr: number;
  fpr: number;
}

export interface RiskMetrics {
  metric: string;
  positive_class: string;
  threshold: number;
  n_samples: number;
  prevalence: number;
  backend: string;
  model_version: string;
  data_version?: string;
  confusion_matrix: RiskConfusionMatrix;
  accuracy: number;
  precision: number;
  recall_sensitivity: number;
  specificity: number;
  npv: number;
  fpr: number;
  f1_score: number;
  youden_index: number;
  matthews_cc: number;
  roc_auc: number | null;
  roc_points: RocPoint[];
  note?: string;
}

export interface DashboardStats {
  total_applications: number;
  pending_review: number;
  approved: number;
  declined: number;
  referred: number;
  approval_rate: number;
  runs_total: number;
  runs_awaiting_human: number;
  avg_run_duration_ms: number;
  decisions_by_day: { day: string; approved: number; declined: number; referred: number }[];
  recent_runs: RunSummary[];
}
