// Response checks of UI-UX-SPEC section 11 ("Validation in src/api.ts"); placeholder values as the spec's fixtures use.
import { afterEach, describe, expect, it, vi } from 'vitest';
import {
  api,
  ApiError,
  ContractError,
  sourceIdsIn,
  validateCompare,
  validateMethod,
  validatePastYears,
  type SavedAnswers,
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

// UI-UX-SPEC §12c: the optional Google sign-in (server: src/fieldshift/api/accounts.py, tests/test_accounts.py)
describe('account requests', () => {
  afterEach(() => vi.unstubAllGlobals());
  const answers: SavedAnswers = { land: 'dry', years: [2010, 2020], priority: 'income' };
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
  it('saves land, years and priority only, and checks the saved set', async () => {
    const fetchMock = reply(201, { id: 7, ...answers });
    vi.stubGlobal('fetch', fetchMock);
    await expect(api.account.save('tok', answers)).resolves.toEqual({ id: 7, ...answers });
    expect(fetchMock.mock.calls[0]?.[1].body).toBe(JSON.stringify(answers));
  });
  it('lists the saved sets and rejects a set of another shape', async () => {
    vi.stubGlobal('fetch', reply(200, { saved: [{ id: 1, ...answers }] }));
    await expect(api.account.saved('tok')).resolves.toEqual([{ id: 1, ...answers }]);
    vi.stubGlobal('fetch', reply(200, { saved: [{ id: 1, ...answers, land: 'wet' }] }));
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
