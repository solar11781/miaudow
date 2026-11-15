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
  type SavedAnswers,
} from './api';
import { PLAN_IDS } from './types';
import { body, compare, facts, method, moneyItem, pastYears, rule, shares, text, value } from './tests/fixtures';

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
  // UI-UX-SPEC section 12d, D-163: "your price and costs" multiplies the study's yield of each money item
  it('rejects a money item without the study yield', () => {
    const withItem = (item: Partial<ReturnType<typeof moneyItem>>) => {
      const r = compare();
      const plan = r.plans[2];
      if (plan) plan.money = { ...plan.money, items: [item] as never[] };
      return r;
    };
    const item: Partial<ReturnType<typeof moneyItem>> = moneyItem('k', '1.03', '40,000', '16,200', '25,000');
    expect(validateCompare(withItem(item), body).plans[2]?.money.items[0]?.yield.value).toBe('1.03');
    delete item.yield;
    expect(() => validateCompare(withItem(item), body)).toThrow(ContractError);
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
  // D-63: the PICSA sentence's source is checked like every other id (H5)
  it('rejects a PICSA source id that is not in sources', () => {
    const r = method();
    r.picsa = { source_ids: ['R-X99'] };
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

// UI-UX-SPEC §12c: the optional Google sign-in (server: src/fieldshift/api/accounts.py, tests/test_accounts.py)
describe('account requests', () => {
  afterEach(() => vi.unstubAllGlobals());
  // D-180: the typed price (đ/kg) and cost (thousand đ/ha) by crop key go with the save
  const answers: SavedAnswers = {
    land: 'canal_end',
    years: [2010, 2020],
    priority: 'income',
    prices: { cc1_spring_peanut: '31357' },
    costs: { cc1_spring_peanut: '24689' },
  };
  const reply = (status: number, json?: unknown) =>
    vi.fn<(path: string, init: RequestInit) => Promise<Response>>(async () =>
      json === undefined ? new Response(null, { status }) : new Response(JSON.stringify(json), { status }),
    );

  it('reads the sign-in config once per page', async () => {
    const fetchMock = reply(200, { available: true, client_id: 'id.apps.googleusercontent.com' });
    vi.stubGlobal('fetch', fetchMock);
    const fresh = await freshApi();
    await expect(fresh.account.config()).resolves.toEqual({
      available: true,
      client_id: 'id.apps.googleusercontent.com',
    });
    await fresh.account.config();
    expect(fetchMock).toHaveBeenCalledTimes(1);
    expect(fetchMock).toHaveBeenCalledWith('/api/account/config', expect.anything());
  });
  it('rejects a config that is on without a client id', async () => {
    vi.stubGlobal('fetch', reply(200, { available: true, client_id: null }));
    await expect((await freshApi()).account.config()).rejects.toThrow(/client_id must be set/);
  });
  it('sends the google token as a bearer header and takes 204 as done', async () => {
    const fetchMock = reply(204);
    vi.stubGlobal('fetch', fetchMock);
    await expect(api.account.signIn('tok')).resolves.toBeUndefined();
    const [path, init] = fetchMock.mock.calls[0] ?? [];
    expect(path).toBe('/api/account/sign-in');
    expect(init?.method).toBe('POST');
    expect(new Headers(init?.headers).get('Authorization')).toBe('Bearer tok');
  });
  it('saves land, years, priority and the typed prices and costs only, and checks the saved set', async () => {
    const fetchMock = reply(201, { id: 7, ...answers });
    vi.stubGlobal('fetch', fetchMock);
    await expect(api.account.save('tok', answers)).resolves.toEqual({ id: 7, ...answers });
    expect(fetchMock.mock.calls[0]?.[1].body).toBe(JSON.stringify(answers));
  });
  it('lists the saved sets and rejects a set of another shape', async () => {
    vi.stubGlobal('fetch', reply(200, { saved: [{ id: 1, ...answers }] }));
    await expect(api.account.saved('tok')).resolves.toEqual([{ id: 1, ...answers }]);
    vi.stubGlobal('fetch', reply(200, { saved: [{ id: 1, ...answers, land: 'dry' }] }));
    await expect(api.account.saved('tok')).rejects.toThrow(ContractError);
  });
  // D-179, D-180: the typed numbers come back only as the page keeps them, crop keys with 1 to 9 ASCII digits
  it.each([
    ['no prices', { prices: undefined }],
    ['a price that is a number', { prices: { cc1_spring_peanut: 31357 } }],
    ['a price of 10 digits', { prices: { cc1_spring_peanut: '1000000000' } }],
    ['a negative cost', { costs: { cc1_spring_peanut: '-3' } }],
    ['a crop key with a dot', { costs: { 'cc1.spring': '3' } }],
    ['a list of costs', { costs: ['3'] }],
  ])('rejects a saved set with %s', async (_, change) => {
    vi.stubGlobal('fetch', reply(200, { saved: [{ id: 1, ...answers, ...change }] }));
    await expect(api.account.saved('tok')).rejects.toThrow(ContractError);
  });
  it('deletes one set and the whole account', async () => {
    const fetchMock = reply(204);
    vi.stubGlobal('fetch', fetchMock);
    await api.account.remove('tok', 7);
    await api.account.deleteAccount('tok');
    expect(fetchMock.mock.calls.map(([p, i]) => `${i.method} ${p}`)).toEqual([
      'DELETE /api/account/saved/7',
      'DELETE /api/account',
    ]);
  });
  it.each([
    [409, 'saved sets are full'],
    [401, 'not signed in'],
    [503, 'sign-in is not available'],
  ])('turns %i into an ApiError with its status', async (status, detail) => {
    vi.stubGlobal('fetch', reply(status, { detail }));
    await expect(api.account.save('tok', answers)).rejects.toEqual(new ApiError(status, detail));
  });
});

// FR-15 and PR #43 (src/fieldshift/api/explain.py, tests/test_explain.py): GET /api/health carries explain: true|false;
// POST /api/explain answers 503 while off, 422 for a body it rejects, 502 when no usable reply came, else {text, ai_generated, model}
describe('explain simply', () => {
  afterEach(() => vi.unstubAllGlobals());
  const reply = (status: number, json: unknown) => vi.fn(async () => new Response(JSON.stringify(json), { status }));
  const request = { answers: body, plan: 'cc1', field: 'evidence', lang: 'vi' } as const;

  it('reads the feature from the explain flag of the health answer, with one GET and no probe', async () => {
    const on = reply(200, { status: 'ok', artifacts: {}, explain: true });
    vi.stubGlobal('fetch', on);
    await expect(explainOn()).resolves.toBe(true);
    expect(on).toHaveBeenCalledTimes(1);
    expect(on).toHaveBeenCalledWith('/api/health', expect.not.objectContaining({ method: 'POST' }));
    vi.stubGlobal('fetch', reply(200, { status: 'ok', artifacts: {}, explain: false }));
    await expect(explainOn()).resolves.toBe(false);
    vi.stubGlobal('fetch', reply(200, { status: 'ok', artifacts: {} }));
    await expect(explainOn()).resolves.toBe(false);
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

// frontend rules "Validation in src/api.ts": every response is checked before a screen uses it (final audit 2026-11-15)
describe('copilot response check', () => {
  afterEach(() => vi.unstubAllGlobals());
  const valid = {
    status: 'grounded',
    engine: 'deterministic',
    model: null,
    answer: 'Các nguồn liên quan:',
    citations: [
      { passage_id: 'p1', source_id: 'R-P02', title: { vi: 'Bài báo', en: 'Paper' }, location: null, url: null },
    ],
    cards: [{ kind: 'plan', ref_id: 'cc1', title: { vi: 'CC1', en: 'CC1' } }],
    tool_trace: [{ tool: 'past_years', input: { year: 2010 }, ok: true }],
    numbers: { checked: 0, unverified: [] },
    missing_information: [],
  };
  const ask = async (json: unknown) => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async () => new Response(JSON.stringify(json), { status: 200 })),
    );
    return (await freshApi()).copilot({ question: 'x', mode: 'simple', lang: 'vi' });
  };

  it('accepts a reply that matches the contract', async () => {
    await expect(ask(valid)).resolves.toEqual(valid);
  });
  it('rejects a reply with a missing answer or a malformed citation', async () => {
    const noAnswer: Record<string, unknown> = { ...valid };
    delete noAnswer.answer;
    await expect(ask(noAnswer)).rejects.toThrow(/copilot\.answer: missing/);
    await expect(ask({ ...valid, citations: [{ passage_id: 'p1' }] })).rejects.toThrow(/copilot\.citations\[0\]/);
    await expect(ask({ ...valid, status: 'made_up' })).rejects.toThrow(/copilot\.status: not one of/);
  });
});
