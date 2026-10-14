import type { Analysis, AnalysisList, EvaluationReport, ExportPayload } from "./types";

export class ApiError extends Error {
  readonly status: number;
  readonly field: string;

  constructor(status: number, message: string, field = "") {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.field = field;
  }
}

export function errorMessage(error: unknown): string {
  if (error instanceof ApiError && error.field) {
    return `${error.field}: ${error.message}`;
  }
  if (error instanceof Error) {
    return error.message;
  }
  return "Request failed";
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(path, {
    ...init,
    headers: {
      Accept: "application/json",
      ...(init?.body ? { "Content-Type": "application/json" } : {}),
      ...init?.headers,
    },
  });
  if (!response.ok) {
    let message = `request failed (${response.status})`;
    let field = "";
    try {
      const body = (await response.json()) as { error?: unknown; field?: unknown };
      if (typeof body.error === "string") {
        message = body.error;
      }
      if (typeof body.field === "string") {
        field = body.field;
      }
    } catch {
      // The status line is enough when the body is not JSON.
    }
    throw new ApiError(response.status, message, field);
  }
  return (await response.json()) as T;
}

export function getHealth(): Promise<{ status: string; version: string }> {
  return request("/api/health");
}

export function getSample(kind: "surfaces" | "python"): Promise<unknown> {
  return request(`/api/sample?kind=${kind}`);
}

export function getEvaluation(): Promise<EvaluationReport> {
  return request("/api/evaluation");
}

export function createAnalysis(payload: unknown): Promise<Analysis> {
  return request("/api/analyses", { method: "POST", body: JSON.stringify(payload) });
}

export function listAnalyses(application: string, offset = 0): Promise<AnalysisList> {
  const params = new URLSearchParams({ limit: "20", offset: String(offset) });
  if (application.trim()) {
    params.set("application", application.trim());
  }
  return request(`/api/analyses?${params.toString()}`);
}

export function getAnalysis(id: number): Promise<Analysis> {
  return request(`/api/analyses/${id}`);
}

export async function downloadExport(id: number, application: string): Promise<void> {
  const payload = await request<ExportPayload>(`/api/analyses/${id}/export`);
  const blob = new Blob([JSON.stringify(payload, null, 2)], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = `${application}-commands.json`;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}
