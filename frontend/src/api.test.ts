// Response checks of UI-UX-SPEC section 11 ("Validation in src/api.ts"); placeholder values as the spec's fixtures use.
import { afterEach, describe, expect, it, vi } from 'vitest';
import { api, ApiError, ContractError, sourceIdsIn, validateCompare, validateMethod, validatePastYears } from './api';
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
    expect(fetchMock).toHaveBeenCalledWith('/api/compare', expect.objectContaining({ method: 'POST', body: JSON.stringify(body) }));
  });
  it('turns a non-2xx status into an ApiError', async () => {
    vi.stubGlobal('fetch', vi.fn(async () => new Response(JSON.stringify({ detail: 'Not Found' }), { status: 404 })));
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
    vi.stubGlobal('fetch', vi.fn(async () => new Response(JSON.stringify({ province: 'nghe_an' }), { status: 200 })));
    await expect((await freshApi()).pastYears()).rejects.toThrow(/rules: missing/);
  });
});
