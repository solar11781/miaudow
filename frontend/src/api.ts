// The only module that talks to the backend (UI-UX-SPEC section 11; frontend rules). Same-origin relative URLs, so
// the farmer's answers go to our own server only, in the POST body (D-92). Every response is checked before a screen
// uses it ("Validation in src/api.ts"); a response that fails the check is an error, never shown.
import type { Bilingual } from './domain/provenance';
import {
  COVERAGE_AXES,
  EXPLAIN_KEYS,
  PLAN_IDS,
  RULE_CODES,
  SEASON_CODES,
  type CompareRequest,
  type CompareResponse,
  type MethodResponse,
  type PastYearsResponse,
  type Plan,
  type Stability,
} from './types';

export class ApiError extends Error {
  constructor(readonly status: number, message: string) {
    super(message);
  }
}

/** A response that does not match the contract of section 11. */
export class ContractError extends Error {}

// ---------------------------------------------------------------- shape checks

type Check = (v: unknown, at: string) => void;

const fail = (at: string, what: string): never => {
  throw new ContractError(`${at}: ${what}`);
};
const isObj = (v: unknown): v is Record<string, unknown> => typeof v === 'object' && v !== null && !Array.isArray(v);

const str: Check = (v, at) => { if (typeof v !== 'string') fail(at, 'not a string'); };
const num: Check = (v, at) => { if (typeof v !== 'number' || !Number.isFinite(v)) fail(at, 'not a number'); };
const bool: Check = (v, at) => { if (typeof v !== 'boolean') fail(at, 'not a boolean'); };
const nullable = (c: Check): Check => (v, at) => { if (v !== null) c(v, at); };
const oneOf = (allowed: readonly string[]): Check => (v, at) => { if (typeof v !== 'string' || !allowed.includes(v)) fail(at, `not one of ${allowed.join(', ')}`); };
const arr = (c: Check): Check => (v, at) => {
  if (!Array.isArray(v)) fail(at, 'not a list');
  (v as unknown[]).forEach((x, i) => c(x, `${at}[${i}]`));
};
const obj = (fields: Record<string, Check>): Check => (v, at) => {
  if (!isObj(v)) return fail(at, 'not an object');
  for (const [k, c] of Object.entries(fields)) {
    if (!(k in v)) fail(`${at}.${k}`, 'missing');
    c(v[k], `${at}.${k}`);
  }
};
const record = (c: Check): Check => (v, at) => {
  if (!isObj(v)) return fail(at, 'not an object');
  for (const [k, x] of Object.entries(v)) c(x, `${at}.${k}`);
};

const text = obj({ vi: str, en: str });
const ids = arr(str);
const value = obj({ value: str, unit: text, source_ids: ids });
const shares = obj(Object.fromEntries(RULE_CODES.map((r) => [r, nullable(value)])));
const season = oneOf(SEASON_CODES);
const sourceFacts = obj({
  id: str, citation: text, study_type: text, place_years: text, read_status: nullable(str),
  full_text_read: nullable(bool), limitations: arr(text), url: nullable(str), nso_credit: bool,
});
const rule = obj({ code: oneOf(RULE_CODES), label: text, rule_text: text, threshold_source_id: str, values_source_ids: ids, computed_by: str });
const span = obj({ first: num, last: num });
const gate = obj({ gate: oneOf(['G1', 'G2', 'G3', 'G4']), season, model_id: nullable(str), passed: nullable(bool), detail: text, source_ids: ids });
const interval = obj({ value: num, ci90_low: num, ci90_high: num });

const pastYearsShape = obj({
  province: oneOf(['nghe_an']), rules: arr(rule), years: arr(obj({ year: num, shares })),
  sources: record(sourceFacts), n_cells: num,
});

const landCheck = obj({ value: nullable(value), principle_source_ids: ids });
const plan = obj({
  id: oneOf(PLAN_IDS), name: text, is_usual: bool,
  calendar: arr(obj({
    crop_key: str, crop_id: str, crop: text, variety: nullable(text), season,
    sow_from: nullable(str), sow_to: nullable(str), harvest_from: nullable(str), harvest_to: nullable(str), source_ids: ids,
  })),
  bare_periods: arr(obj({ from: str, to: str })),
  money: obj({
    items: arr(obj({ crop_key: str, crop: text, season, profit: value, cost: nullable(value), flag: nullable(text) })),
    total: nullable(value), price_year: nullable(str), definition: text, text_only: nullable(text),
  }),
  exposure: arr(obj({
    crop_key: str, crop: text,
    per_year: arr(obj({ year: num, shares, soil_wetness: obj({ value: nullable(value), normal: nullable(value) }) })),
  })),
  stability: nullable(arr(obj({
    crop_key: str, season, label: text, model_status: oneOf(['shown', 'not_shown', 'not_modeled']), years_count: num, scope: text,
    per_year: arr(obj({ year: num, real: nullable(value), oos_prediction: nullable(value), range_80: nullable(obj({ low: value, high: value })) })),
    summary: nullable(obj({ min: value, median: value, max: value })), worst_years: arr(num),
  }))),
  water: arr(obj({ crop_key: str, measure: oneOf(['to_apply', 'crop_uses', 'not_listed']), value: nullable(value), scope: nullable(text), note: nullable(text) })),
  land: obj({ crops_in_year: landCheck, living_days: landCheck, legume: obj({ present: bool, crops: arr(text), principle_source_ids: ids }) }),
  why: obj({ why: text, evidence: text, benefits: text, gaps: text, risks: arr(obj({ text, source_ids: ids })) }),
});
const compareShape = obj({
  request: obj({ province: oneOf(['nghe_an']), land: oneOf(['dry', 'unsure']), years: arr(num), priority: oneOf(['income', 'stability', 'water', 'land']) }),
  test_years: span, n_cells: num,
  seasons: arr(obj({ code: season, label: text, window: text, source_ids: ids })),
  rules: arr(rule), gates: arr(gate), plans: arr(plan), sources: record(sourceFacts),
});

const methodShape = obj({
  test_years: span, freeze_commit: str,
  metrics: arr(obj({
    model_id: oneOf(['b0', 'b2', 'bnw', 'm1_ridge', 'm2_lgbm', 'm3_rf']), season, role: oneOf(['primary', 'secondary', 'reference']),
    scheme: oneOf(['rolling_origin', 'spatial_holdout']),
    sensitivity: nullable(oneOf(['no_fao_flagged', 'mae_skill', 'risk_level_features', 'window', 'centroid_points'])),
    detail: nullable(text), subset: str, rmse: nullable(num), mae: nullable(num), r2_oos: nullable(num),
    skill_vs_b0: nullable(interval), skill_vs_b2: nullable(interval), skill_vs_bnw: nullable(interval),
    coverage_80: nullable(num), n_rows: num, n_test_years: num, source_ids: ids,
  })),
  gates: arr(gate),
  weather_claims: arr(obj({ season, model_id: str, made: bool, source_ids: ids })),
  reports: arr(obj({ id: str, title: text, text, source_ids: ids })),
  coverage: arr(obj({ row_key: str, crop: text, axis: oneOf(COVERAGE_AXES), text, source_ids: ids })),
  explain_terms: arr(obj({ key: oneOf(EXPLAIN_KEYS), title: text, text, source_ids: ids })),
  limitations: arr(text),
  rain_check: nullable(obj({ months: arr(obj({ month: str, imerg: value, power: value })), cc: value, mean_imerg: value, mean_power: value, source_ids: ids })),
  sources: record(sourceFacts),
});

// ---------------------------------------------------------------- content checks

const ID_LISTS = ['source_ids', 'values_source_ids', 'principle_source_ids'];
const ID_SINGLES = ['threshold_source_id', 'computed_by'];

/** Every id the id fields hold, outside `sources` (the same walk as schemas.source_ids_in). */
export function sourceIdsIn(node: unknown): string[] {
  if (Array.isArray(node)) return node.flatMap(sourceIdsIn);
  if (!isObj(node)) return [];
  return Object.entries(node).flatMap(([k, v]) => {
    if (ID_LISTS.includes(k)) return v as string[];
    if (ID_SINGLES.includes(k)) return [v as string];
    return k === 'sources' ? [] : sourceIdsIn(v);
  });
}

function checkSources(res: { sources: Record<string, { id: string }> }) {
  const missing = [...new Set(sourceIdsIn(res))].filter((id) => !(id in res.sources));
  if (missing.length) fail('sources', `ids not in sources: ${missing.join(', ')}`);
  for (const [k, f] of Object.entries(res.sources)) if (f.id !== k) fail(`sources.${k}`, 'listed under another id');
}

const ascending = (xs: number[]) => xs.every((x, i) => i === 0 || (xs[i - 1] as number) < x);
const sameList = (a: readonly unknown[], b: readonly unknown[]) => a.length === b.length && a.every((x, i) => x === b[i]);
const inYear = (d: (string | null)[]) => d.every((x) => x === null) || (d.every((x) => x !== null) && sameList(d, [...d].sort()));

export function validatePastYears(raw: unknown): PastYearsResponse {
  pastYearsShape(raw, 'past-years');
  const res = raw as PastYearsResponse;
  if (!sameList(res.rules.map((r) => r.code), RULE_CODES)) fail('rules', 'not the five rules in order');
  if (!res.years.length || !ascending(res.years.map((y) => y.year))) fail('years', 'empty or not strictly ascending');
  checkSources(res);
  return res;
}

function checkStability(st: Stability, first: number, last: number) {
  const real = st.per_year.filter((y) => y.real !== null).length;
  if ((st.summary === null) !== (real < 2)) fail(st.crop_key, 'summary must be null exactly when fewer than 2 real values');
  for (const y of st.per_year) {
    const at = `${st.crop_key} ${y.year}`;
    if (y.range_80 !== null && y.oos_prediction === null) fail(at, 'range_80 without oos_prediction');
    if (y.oos_prediction !== null && (y.year < first || y.year > last)) fail(at, 'prediction outside test years');
  }
}

function checkPlan(p: Plan, years: number[], first: number, last: number) {
  for (const c of p.calendar) if (!inYear([c.sow_from, c.sow_to, c.harvest_from, c.harvest_to])) fail(c.crop_key, 'dates not all set in order or all null');
  for (const b of [...p.exposure, ...(p.stability ?? [])]) if (!sameList(b.per_year.map((y) => y.year), years)) fail(b.crop_key, 'per_year is not the requested years');
  for (const st of p.stability ?? []) checkStability(st, first, last);
}

const sameRequest = (r: CompareRequest, sent: CompareRequest) =>
  r.province === sent.province && r.land === sent.land && r.priority === sent.priority && sameList(r.years, sent.years);

export function validateCompare(raw: unknown, sent: CompareRequest): CompareResponse {
  compareShape(raw, 'compare');
  const res = raw as CompareResponse;
  if (!sameRequest(res.request, sent)) fail('request', 'does not equal the body sent');
  if (!sameList(res.plans.map((p) => p.id), PLAN_IDS)) fail('plans', 'not the six plans in canonical order');
  for (const p of res.plans) checkPlan(p, sent.years, res.test_years.first, res.test_years.last);
  checkSources(res);
  return res;
}

export function validateMethod(raw: unknown): MethodResponse {
  methodShape(raw, 'method');
  const res = raw as MethodResponse;
  const cells = res.coverage.map((c) => `${c.row_key}|${c.axis}`);
  if (new Set(cells).size !== cells.length) fail('coverage', 'a (row_key, axis) occurs twice');
  if (!sameList(res.explain_terms.map((e) => e.key), EXPLAIN_KEYS)) fail('explain_terms', 'not the six keys in order');
  checkSources(res);
  return res;
}

// ---------------------------------------------------------------- requests

async function call(path: string, init: RequestInit & { timeoutMs?: number } = {}): Promise<unknown> {
  const ctrl = new AbortController();
  const timer = window.setTimeout(() => ctrl.abort(), init.timeoutMs ?? 20000);
  const outer = init.signal;
  outer?.addEventListener('abort', () => ctrl.abort(), { once: true });
  try {
    const res = await fetch(`/api${path}`, { ...init, signal: ctrl.signal, headers: { 'Content-Type': 'application/json', ...init.headers } });
    if (!res.ok) {
      const body: unknown = await res.json().catch(() => ({}));
      throw new ApiError(res.status, isObj(body) && typeof body.detail === 'string' ? body.detail : res.statusText);
    }
    return await res.json();
  } finally {
    window.clearTimeout(timer);
  }
}

/** The method page's grid figure (UI-UX-SPEC section 11b item 4), served by our backend. */
export const GRID_FIGURE_URL = '/api/figures/nghe_an_grid.svg';

// the past-years response is kept in memory for the life of the page (section 11), never stored in the browser
let pastYearsOnce: Promise<PastYearsResponse> | null = null;

export const api = {
  pastYears(signal?: AbortSignal): Promise<PastYearsResponse> {
    pastYearsOnce ??= call('/past-years?province=nghe_an', { signal }).then(validatePastYears);
    pastYearsOnce.catch(() => { pastYearsOnce = null; });
    return pastYearsOnce;
  },
  compare: async (body: CompareRequest, signal?: AbortSignal): Promise<CompareResponse> =>
    validateCompare(await call('/compare', { method: 'POST', body: JSON.stringify(body), signal }), body),
  method: async (signal?: AbortSignal): Promise<MethodResponse> => validateMethod(await call('/method', { signal })),
  health: (signal?: AbortSignal) => call('/health', { signal, timeoutMs: 4000 }) as Promise<Health>,
  copilot: (body: CopilotRequest, signal?: AbortSignal) =>
    call('/copilot', { method: 'POST', body: JSON.stringify(body), signal, timeoutMs: 90000 }) as Promise<CopilotResponse>,
};

// ---------------------------------------------------------------- member B's copilot contract (its own backend)

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
