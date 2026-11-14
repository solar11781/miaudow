// Response checks of UI-UX-SPEC section 11 ("Validation in src/api.ts"); placeholder values as the spec's fixtures use.
import { afterEach, describe, expect, it, vi } from 'vitest';
import { api, ApiError, ContractError, sourceIdsIn, validateCompare, validateMethod, validatePastYears } from './api';
import { EXPLAIN_KEYS, PLAN_IDS, RULE_CODES, type CompareRequest } from './types';

const text = { vi: 'x', en: 'x' };
const facts = (id: string) => ({ id, citation: text, study_type: text, place_years: text, read_status: null, full_text_read: null, limitations: [], url: null, nso_credit: false });
const value = (ids = ['R-N01']) => ({ value: 'xx', unit: text, source_ids: ids });
const shares = () => Object.fromEntries(RULE_CODES.map((r) => [r, value()]));
const rule = (code: string) => ({ code, label: text, rule_text: text, threshold_source_id: 'R-A01', values_source_ids: ['R-N01'], computed_by: 'E-019' });
const sources = { 'R-A01': facts('R-A01'), 'R-N01': facts('R-N01'), 'E-019': facts('E-019'), 'R-P02': facts('R-P02') };

const pastYears = () => ({
  province: 'nghe_an',
  rules: RULE_CODES.map(rule),
  years: [{ year: 1995, shares: shares() }, { year: 1996, shares: { ...shares(), cold: null } }],
  sources,
  n_cells: 5,
});

const body: CompareRequest = { province: 'nghe_an', land: 'dry', years: [2010, 2020], priority: 'income' };
const land = { value: value(), principle_source_ids: ['R-P02'] };
const plan = (id: string) => ({
  id, name: text, is_usual: id.startsWith('usual'),
  calendar: [{ crop_key: `${id}_spring_rice`, crop_id: 'rice', crop: text, variety: null, season: 'spring', sow_from: '02-01', sow_to: '02-01', harvest_from: '05-01', harvest_to: '05-01', source_ids: ['R-P02'] }],
  bare_periods: [{ from: '05-02', to: '01-31' }],
  money: { items: [], total: null, price_year: null, definition: text, text_only: null },
  exposure: [{ crop_key: `${id}_spring_rice`, crop: text, per_year: body.years.map((year) => ({ year, shares: shares(), soil_wetness: { value: value(), normal: null } })) }],
  stability: [{
    crop_key: `${id}_spring_rice`, season: 'spring', label: text, model_status: 'not_shown', years_count: 2, scope: text,
    per_year: body.years.map((year) => ({ year, real: value(), oos_prediction: null, range_80: null })),
    summary: { min: value(), median: value(), max: value() }, worst_years: [2010],
  }],
  water: [{ crop_key: `${id}_spring_rice`, measure: 'not_listed', value: null, scope: null, note: null }],
  land: { crops_in_year: land, living_days: land, legume: { present: false, crops: [], principle_source_ids: ['R-P02'] } },
  why: { why: text, evidence: text, benefits: text, gaps: text, risks: [{ text, source_ids: [] }] },
});
const compare = () => ({
  request: { ...body }, test_years: { first: 2016, last: 2024 }, n_cells: 5,
  seasons: [{ code: 'spring', label: text, window: text, source_ids: ['R-P02'] }],
  rules: RULE_CODES.map(rule), gates: [], plans: PLAN_IDS.map(plan), sources,
});
const method = () => ({
  test_years: { first: 2016, last: 2024 }, freeze_commit: 'x', metrics: [], gates: [], weather_claims: [], reports: [],
  coverage: [{ row_key: 'r', crop: text, axis: 'money', text, source_ids: ['R-P02'] }],
  explain_terms: EXPLAIN_KEYS.map((key) => ({ key, title: text, text, source_ids: ['R-P02'] })),
  limitations: [text], rain_check: null, sources,
});

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
