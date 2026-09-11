/** Typed API client for the backend (Team A). Codes strictly to the API contract. */

import { getToken } from "@/lib/session";
import type {
  Application,
  CreateApplicationPayload,
  CreditMemo,
  DashboardStats,
  Document,
  HealthResponse,
  LoginResponse,
  PolicyProfile,
  ReplayResponse,
  ResumePayload,
  RiskMetrics,
  RunState,
  RunSummary,
  TraceResponse,
  UnderwriteResponse,
  WhatIfRequest,
  WhatIfResponse,
} from "@/lib/types";

export const BASE_URL = process.env.NEXT_PUBLIC_BACKEND_URL ?? "http://localhost:8000";

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

interface RequestOptions extends Omit<RequestInit, "body"> {
  /** JSON body; serialised and sent with Content-Type: application/json. */
  json?: unknown;
  /** Raw body (e.g. FormData) sent as-is. */
  body?: BodyInit | null;
}

async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const { json, body, headers: initHeaders, ...init } = options;
  const headers = new Headers(initHeaders);
  const token = getToken();
  if (token && !headers.has("Authorization")) headers.set("Authorization", `Bearer ${token}`);
  let finalBody: BodyInit | null | undefined = body;
  if (json !== undefined) {
    headers.set("Content-Type", "application/json");
    finalBody = JSON.stringify(json);
  }

  let res: Response;
  try {
    res = await fetch(`${BASE_URL}${path}`, { ...init, headers, body: finalBody });
  } catch {
    throw new ApiError(0, `Cannot reach backend at ${BASE_URL}. Is it running?`);
  }

  if (!res.ok) {
    let detail = `API error ${res.status}`;
    try {
      const payload = (await res.json()) as { detail?: unknown };
      if (typeof payload.detail === "string") detail = payload.detail;
      else if (payload.detail !== undefined) detail = JSON.stringify(payload.detail);
    } catch {
      // non-JSON error body
    }
    throw new ApiError(res.status, detail);
  }
  if (res.status === 204) return undefined as T;
  return (await res.json()) as T;
}

export function errorMessage(err: unknown): string {
  if (err instanceof Error) return err.message;
  return String(err);
}

export const api = {
  // Auth
  login: (email: string, password: string) =>
    request<LoginResponse>("/auth/login", { method: "POST", json: { email, password } }),

  // Applications
  listApplications: () => request<Application[]>("/applications"),
  getApplication: (id: string) => request<Application>(`/applications/${id}`),
  createApplication: (payload: CreateApplicationPayload) =>
    request<Application>("/applications", { method: "POST", json: payload }),

  // Documents
  listDocuments: (applicationId: string) =>
    request<Document[]>(`/applications/${applicationId}/documents`),
  uploadDocument: (applicationId: string, file: File, category?: string) => {
    const form = new FormData();
    form.append("file", file);
    if (category) form.append("category", category);
    return request<Document>(`/applications/${applicationId}/documents`, {
      method: "POST",
      body: form,
    });
  },
  deleteDocument: (documentId: string) =>
    request<void>(`/documents/${documentId}`, { method: "DELETE" }),

  // Underwriting
  startUnderwrite: (applicationId: string, policyProfile?: PolicyProfile) =>
    request<UnderwriteResponse>(`/applications/${applicationId}/underwrite`, {
      method: "POST",
      json: policyProfile ? { policy_profile: policyProfile } : {},
    }),
  getRun: (runId: string) => request<RunState>(`/underwriting/${runId}`),
  resumeRun: (runId: string, payload: ResumePayload) =>
    request<RunState>(`/underwriting/${runId}/resume`, { method: "POST", json: payload }),
  getTrace: (runId: string) => request<TraceResponse>(`/underwriting/${runId}/trace`),
  getReplay: (runId: string) => request<ReplayResponse>(`/underwriting/${runId}/replay`),
  whatIf: (runId: string, payload: WhatIfRequest) =>
    request<WhatIfResponse>(`/underwriting/${runId}/what-if`, { method: "POST", json: payload }),

  // Credit memo
  getCreditMemo: (applicationId: string) =>
    request<CreditMemo>(`/applications/${applicationId}/credit-memo`),
  creditMemoPdfUrl: (applicationId: string) =>
    `${BASE_URL}/applications/${applicationId}/credit-memo?format=pdf`,
  /** Auto-generated PDF for a specific run (rendered on completion, cached by the backend). */
  runMemoPdfUrl: (runId: string) => `${BASE_URL}/underwriting/${runId}/memo.pdf`,

  // System
  health: () => request<HealthResponse>("/health"),
  riskMetrics: (threshold = 0.5, n = 800) =>
    request<RiskMetrics>(`/risk/metrics?threshold=${threshold}&n=${n}`),

  // Dashboard / audit
  dashboardStats: () => request<DashboardStats>("/dashboard/stats"),
  auditRuns: () => request<RunSummary[]>("/audit/runs"),

  /** Kept for backwards compatibility with the scaffold. */
  getDecision: (runId: string) => request<RunState>(`/underwriting/${runId}`),
};
