// Typed client of the MIAUDOW API (api/miaudow_api/contracts.py). The API key of any language model stays on the
// server: the browser only ever talks to /api.
import type { Bilingual } from '../domain/provenance';

export type CopilotStatus = 'grounded' | 'reference_only' | 'insufficient_evidence' | 'provider_error' | 'not_configured';
export type WaterSituation = 'canal_end' | 'high_field' | 'reliable' | 'water_short';

export interface CopilotRequest {
  question: string;
  mode: 'simple' | 'technical';
  lang: 'vi' | 'en';
  water?: WaterSituation | null;
}

export interface Citation { passage_id: string; source_id: string; title: Bilingual; location: string | null; url: string | null }
export interface AnswerCard { kind: 'plan' | 'year' | 'metric' | 'passage'; ref_id: string; title: Bilingual }
export interface ToolCall { tool: string; input: Record<string, unknown>; ok: boolean }

export interface CopilotResponse {
  status: CopilotStatus;
  engine: 'claude' | 'deterministic';
  model: string | null;
  answer: string;
  citations: Citation[];
  cards: AnswerCard[];
  tool_trace: ToolCall[];
  numbers: { checked: number; unverified: string[] };
  missing_information: Bilingual[];
}

export interface Health {
  status: string;
  copilot?: { engine?: string; configured?: boolean } | string;
  [key: string]: unknown;
}

export class ApiError extends Error {
  constructor(readonly status: number, message: string) {
    super(message);
  }
}

async function call<T>(path: string, init: RequestInit & { timeoutMs?: number } = {}): Promise<T> {
  const ctrl = new AbortController();
  const timer = window.setTimeout(() => ctrl.abort(), init.timeoutMs ?? 20000);
  const outer = init.signal;
  outer?.addEventListener('abort', () => ctrl.abort(), { once: true });
  try {
    const res = await fetch(`api${path}`, { ...init, signal: ctrl.signal, headers: { 'Content-Type': 'application/json', ...init.headers } });
    if (!res.ok) {
      const body = await res.json().catch(() => ({}));
      throw new ApiError(res.status, typeof body.detail === 'string' ? body.detail : res.statusText);
    }
    return (await res.json()) as T;
  } finally {
    window.clearTimeout(timer);
  }
}

export const api = {
  health: (signal?: AbortSignal) => call<Health>('/health', { signal, timeoutMs: 4000 }),
  copilot: (body: CopilotRequest, signal?: AbortSignal) =>
    call<CopilotResponse>('/copilot', { method: 'POST', body: JSON.stringify(body), signal, timeoutMs: 90000 }),
};
