// Response checks of UI-UX-SPEC section 11 ("Validation in src/api.ts"); placeholder values as the spec's fixtures use.
import { afterEach, describe, expect, it, vi } from 'vitest';
import {
  api,
  ApiError,
  ContractError,
  explainOn,
  explainSimply,
  SNAPSHOT_MODE,
  sourceIdsIn,
  validateCompare,
  validateMethod,
  validatePastYears,
} from './api';
import { PLAN_IDS } from './types';
import { body, compare, facts, method, pastYears, rule, shares, text, value } from './tests/fixtures';

describe('past years check', () => {
  it('accepts a response of the contract', () => {
    expect(validatePastYears(pastYears()).years).toHaveLength(2);
  });
  it('rejects rules out of order', () => {
    const r = pastYears();
    r.rules.reverse();
    expect(() => validatePastYears(r)).toThrow(ContractError);
  });
  it('rejects years that are not strictly ascending', () => {
    const r = pastYears();
    r.years.reverse();
    expect(() => validatePastYears(r)).toThrow(/ascending/);
  });
  it('rejects a source id that is not in sources (H5)', () => {
    const r = pastYears();
    r.years[0] = { year: 1995, shares: { ...shares(), heat: value(['R-X99']) } };
    expect(() => validatePastYears(r)).toThrow(/R-X99/);
  });
  it('rejects a Text without English', () => {
    const r = pastYears();
    r.rules[0] = { ...rule('heavy_rain'), label: { vi: 'x' } as typeof text };
    expect(() => validatePastYears(r)).toThrow(/label\.en/);
  });
});

describe('compare check', () => {
  it('accepts a response of the contract', () => {
    expect(validateCompare(compare(), body).plans.map((p) => p.id)).toEqual(PLAN_IDS);
  });
  it('rejects a response whose request differs from the body sent', () => {
    expect(() => validateCompare(compare(), { ...body, years: [2010] })).toThrow(/request/);
  });
  it('rejects plans in another order (H3)', () => {
    const r = compare();
    r.plans.reverse();
    expect(() => validateCompare(r, body)).toThrow(/order/);
  });
  it('rejects a span with only some dates', () => {
    const r = compare();
    const span = r.plans[2]?.calendar[0];
    if (span) span.sow_to = null as unknown as string;
    expect(() => validateCompare(r, body)).toThrow(/dates/);
  });
  it('rejects a prediction outside the test years', () => {
    const r = compare();
    const row = r.plans[0]?.stability[0]?.per_year[0];
    if (row) row.oos_prediction = value() as unknown as null;
    expect(() => validateCompare(r, body)).toThrow(/test years/);
  });
  it('rejects a summary with fewer than 2 real values', () => {
    const r = compare();
    const row = r.plans[0]?.stability[0]?.per_year[0];
    if (row) row.real = null as unknown as ReturnType<typeof value>;
    expect(() => validateCompare(r, body)).toThrow(/summary/);
  });
});

describe('method check', () => {
  it('accepts a response of the contract', () => {
    expect(validateMethod(method()).explain_terms).toHaveLength(6);
  });
  it('rejects a response without the datasets not used (section 11, D-165)', () => {
    const r: Record<string, unknown> = method();
    delete r.datasets_not_used;
    expect(() => validateMethod(r)).toThrow(/datasets_not_used/);
  });
  it('rejects a source id of a dataset not used that is not in sources', () => {
    const r = method();
    r.datasets_not_used = [{ dataset: 'x', reason: text, source_ids: ['R-X99'] }];
    expect(() => validateMethod(r)).toThrow(/R-X99/);
  });
  it('rejects a coverage cell listed twice', () => {
    const r = method();
    r.coverage.push({ ...r.coverage[0] } as (typeof r.coverage)[0]);
    expect(() => validateMethod(r)).toThrow(/coverage/);
  });
});

describe('source ids', () => {
  it('collects every id field outside sources', () => {
    expect(sourceIdsIn({ a: rule('heat'), sources: { 'R-Z': facts('R-Z') } })).toEqual(['R-A01', 'R-N01', 'E-019']);
  });
});

// a new module instance, so the in-memory past-years response of another test is not reused
const freshApi = async () => {
  vi.resetModules();
  return (await import('./api')).api;
};

describe('requests', () => {
  afterEach(() => vi.unstubAllGlobals());

  it('posts the answers in the body to the same-origin path', async () => {
    const fetchMock = vi.fn(async () => new Response(JSON.stringify(compare()), { status: 200 }));
    vi.stubGlobal('fetch', fetchMock);
    await api.compare(body);
    expect(fetchMock).toHaveBeenCalledWith(
      '/api/compare',
      expect.objectContaining({ method: 'POST', body: JSON.stringify(body) }),
    );
  });
  // UI-UX-SPEC section 11: "There is no app-level timeout"; the browser's own network behaviour applies
  it('sets no app-level timeout on the product calls', async () => {
    vi.useFakeTimers();
    const signals: (AbortSignal | null | undefined)[] = [];
    vi.stubGlobal(
      'fetch',
      vi.fn((_: string, init: RequestInit) => {
        signals.push(init.signal);
        return new Promise<Response>(() => undefined);
      }),
    );
    void api.compare(body);
    void api.method();
    await vi.advanceTimersByTimeAsync(10 * 60 * 1000);
    expect(signals.map((s) => s?.aborted)).toEqual([false, false]);
    vi.useRealTimers();
  });
  it('turns a non-2xx status into an ApiError', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async () => new Response(JSON.stringify({ detail: 'Not Found' }), { status: 404 })),
    );
    await expect(api.method()).rejects.toEqual(new ApiError(404, 'Not Found'));
  });
  it('loads past years once per page, shared by every screen and never cancelled by one (section 11)', async () => {
    const fetchMock = vi.fn(async (_: string, init: RequestInit) => {
      await Promise.resolve();
      if (init.signal?.aborted) throw new DOMException('aborted', 'AbortError');
      return new Response(JSON.stringify(pastYears()), { status: 200 });
    });
    vi.stubGlobal('fetch', fetchMock);
    const fresh = await freshApi();
    const first = fresh.pastYears();
    await expect(fresh.pastYears()).resolves.toBe(await first);
    expect(fetchMock).toHaveBeenCalledTimes(1);
  });
  it('rejects a response that fails the check', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async () => new Response(JSON.stringify({ province: 'nghe_an' }), { status: 200 })),
    );
    await expect((await freshApi()).pastYears()).rejects.toThrow(/rules: missing/);
  });
});

// FR-15 and PR #43 (src/fieldshift/api/explain.py, tests/test_explain.py): POST /api/explain answers 503 while off
// before it reads the body, 422 for a body it rejects, 502 when no usable reply came, else {text, ai_generated, model}
describe('explain simply', () => {
  afterEach(() => vi.unstubAllGlobals());
  const reply = (status: number, json: unknown) => vi.fn(async () => new Response(JSON.stringify(json), { status }));
  const request = { answers: body, plan: 'cc1', field: 'evidence', lang: 'vi' } as const;

  it('reads the feature as off from a 503 and as on from a 422 to an empty body', async () => {
    const off = reply(503, { detail: 'Service Unavailable' });
    vi.stubGlobal('fetch', off);
    await expect(explainOn()).resolves.toBe(false);
    expect(off).toHaveBeenCalledWith('/api/explain', expect.objectContaining({ method: 'POST', body: '{}' }));
    vi.stubGlobal('fetch', reply(422, { detail: [] }));
    await expect(explainOn()).resolves.toBe(true);
  });
  it('reads the feature as off when the check cannot reach the server', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async () => {
        throw new TypeError('offline');
      }),
    );
    await expect(explainOn()).resolves.toBe(false);
  });
  it('posts the answers, plan, part and language and returns the checked reply', async () => {
    const ok = reply(200, { text: 'Lời dễ hiểu', ai_generated: true, model: 'claude-haiku-5-5' });
    vi.stubGlobal('fetch', ok);
    await expect(explainSimply(request)).resolves.toEqual({
      text: 'Lời dễ hiểu',
      ai_generated: true,
      model: 'claude-haiku-5-5',
    });
    expect(ok).toHaveBeenCalledWith(
      '/api/explain',
      expect.objectContaining({ method: 'POST', body: JSON.stringify(request) }),
    );
  });
  it.each([
    [{ text: 'x', ai_generated: false, model: 'm' }, /ai_generated/],
    [{ text: 'x', model: 'm' }, /ai_generated: missing/],
    [{ text: 3, ai_generated: true, model: 'm' }, /text: not a string/],
    [{ text: '  ', ai_generated: true, model: 'm' }, /text: empty/],
  ])('rejects a reply of another shape (%j)', async (json, error) => {
    vi.stubGlobal('fetch', reply(200, json));
    await expect(explainSimply(request)).rejects.toThrow(error);
  });
  it('turns 502 and 503 into an ApiError with the status', async () => {
    vi.stubGlobal('fetch', reply(502, { detail: 'Bad Gateway' }));
    await expect(explainSimply(request)).rejects.toEqual(new ApiError(502, 'Bad Gateway'));
    vi.stubGlobal('fetch', reply(503, { detail: 'Service Unavailable' }));
    await expect(explainSimply(request)).rejects.toEqual(new ApiError(503, 'Service Unavailable'));
  });
});

// 04-TECH-DESIGN section 9 runbook: the demo-day fallback reads the saved real answers of scripts/build_snapshot.py
describe('snapshot mode (npm run build:snapshot only)', () => {
  const saved = [{ land: 'dry', priority: 'income', years: [2010, 2020], file: 'compare/dry-income-2010_2020.json' }];
  const index = { commit: 'abc', made_at: '2026-11-14T16:58:56+00:00', compare: saved };
  const serve = (files: Record<string, unknown>) => {
    const fetchMock = vi.fn(async (url: string) => {
      const hit = Object.entries(files).find(([name]) => url.endsWith(`snapshot/${name}`));
      return hit ? new Response(JSON.stringify(hit[1]), { status: 200 }) : new Response('{}', { status: 404 });
    });
    vi.stubGlobal('fetch', fetchMock);
    return fetchMock;
  };
  const snapshotApi = async () => {
    vi.stubEnv('MODE', 'snapshot');
    vi.resetModules();
    return import('./api');
  };
  afterEach(() => {
    vi.unstubAllGlobals();
    vi.unstubAllEnvs();
  });

  it('is off in the normal build, which calls /api', () => {
    expect(SNAPSHOT_MODE).toBe(false);
  });
  it('answers saved choices from the saved compare file and never calls /api', async () => {
    const fetchMock = serve({ 'index.json': index, 'compare/dry-income-2010_2020.json': compare() });
    const snap = await snapshotApi();
    expect(snap.SNAPSHOT_MODE).toBe(true);
    await expect(snap.api.compare(body)).resolves.toMatchObject({ request: body });
    expect(fetchMock.mock.calls.map(([url]) => url).filter((url) => url.includes('/api'))).toEqual([]);
  });
  it('answers other choices with the list of saved ones', async () => {
    serve({ 'index.json': index });
    const snap = await snapshotApi();
    const miss = snap.api.compare({ ...body, priority: 'water' });
    await expect(miss).rejects.toBeInstanceOf(snap.SnapshotMissError);
    await expect(miss).rejects.toMatchObject({ saved });
  });
  it('reads past years, the method and the made-at time from the snapshot, with the same checks', async () => {
    serve({ 'index.json': index, 'past-years.json': pastYears(), 'method.json': { test_years: 1 } });
    const snap = await snapshotApi();
    await expect(snap.api.pastYears()).resolves.toMatchObject({ province: 'nghe_an' });
    await expect(snap.api.snapshot()).resolves.toMatchObject({ made_at: index.made_at });
    await expect(snap.api.method()).rejects.toThrow(snap.ContractError);
    expect(snap.GRID_FIGURE_URL).toMatch(/snapshot\/figures\/nghe_an_grid\.svg$/);
  });
  it('rejects an index whose file is outside the compare folder', async () => {
    serve({ 'index.json': { ...index, compare: [{ ...saved[0], file: '../secret.json' }] } });
    const snap = await snapshotApi();
    await expect(snap.api.compare(body)).rejects.toThrow(/file/);
  });
  it('rejects an index whose made_at is not a date, so the notice cannot break the page', async () => {
    serve({ 'index.json': { ...index, made_at: 'yesterday' } });
    const snap = await snapshotApi();
    await expect(snap.api.snapshot()).rejects.toThrow(/made_at/);
  });
  // no live answer may appear under the offline notice
  it('rejects the copilot and health calls at once, calling nothing', async () => {
    const fetchMock = serve({});
    const snap = await snapshotApi();
    await expect(snap.api.copilot({ question: 'x', mode: 'simple', lang: 'vi' })).rejects.toThrow(/offline/);
    await expect(snap.api.health()).rejects.toThrow(/offline/);
    expect(fetchMock).not.toHaveBeenCalled();
  });
});
