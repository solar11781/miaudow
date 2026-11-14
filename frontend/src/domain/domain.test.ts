import { describe, expect, it } from 'vitest';
import { hazards, model, YEARS } from '../data';
import { bareMonths, dateRange, dayOfYear, livingDays, periodPieces, segments, spanSegments } from './calendar';
import { cropShare, cropShareRange, RULES, soilReading, yearShare } from './hazards';
import { compareRequest, parseFarmerState, serializeFarmerState, toggleYear, MAX_YEARS } from './farmerState';
import { planById, planProfitMillion, PLANS } from './plans';
import { riceSummary, riceYear, seasonStatus } from './rice';
import { SOURCES } from './sources';

const plan = (id: Parameters<typeof planById>[0]) => {
  const p = planById(id);
  if (!p) throw new Error(id);
  return p;
};

describe('calendar', () => {
  it('counts days of a non-leap year', () => {
    expect(dayOfYear('01-01')).toBe(1);
    expect(dayOfYear('03-01')).toBe(60);
    expect(dayOfYear('12-31')).toBe(365);
    expect(() => dayOfYear('13-01')).toThrow();
  });
  it('puts overlapping reported dates on separate lanes', () => {
    expect(Math.max(...segments(plan('cc2')).map((s) => s.lane))).toBe(1); // chili to 25/6, soybean from 10/6
    expect(Math.max(...segments(plan('cc5')).map((s) => s.lane))).toBe(1); // black bean to 25/8, sweet potato from 15/8
    expect(Math.max(...segments(plan('cc4')).map((s) => s.lane))).toBe(0);
  });
  it('counts living days and bare months from the trial dates', () => {
    expect(livingDays(plan('cc4'))).toBe(79 + 72 + 89);
    expect(bareMonths(plan('cc4'))).toEqual([5]);
    expect(bareMonths(plan('p03'))).toEqual([]);
  });
});

describe('plans (P-02 Table 13)', () => {
  it('adds the published per-crop profits', () => {
    const totals = Object.fromEntries(PLANS.map((p) => [p.id, planProfitMillion(p)]));
    expect(totals).toEqual({ cc5: 30.799, p03: null, cc1: 53.38, cc2: 53.665, cc3: 55.36, cc4: 58.765 });
  });
  it('keeps every crop window inside one calendar year', () => {
    for (const p of PLANS) for (const c of p.crops) expect(dayOfYear(c.harvest)).toBeGreaterThan(dayOfYear(c.sow));
  });
  it('uses the same field dates as the generated hazard data', () => {
    for (const p of PLANS)
      for (const c of p.crops) expect(hazards.crops[c.key]).toEqual({ sow: c.sow, harvest: c.harvest });
  });
});

describe('hazard data', () => {
  it('has farmland weights that sum to one and 30 years', () => {
    expect(hazards.cells.reduce((s, c) => s + c.weight, 0)).toBeCloseTo(1, 2);
    expect(YEARS).toHaveLength(30);
    expect(YEARS[0]).toBe(1995);
  });
  it('reads shares exactly as generated, all within 0..1', () => {
    for (const rule of Object.keys(RULES) as (keyof typeof RULES)[]) {
      YEARS.forEach((y, i) => {
        expect(yearShare(rule, y)).toBe(hazards.year_level[rule][i]);
        expect(yearShare(rule, y)).toBeGreaterThanOrEqual(0);
        expect(yearShare(rule, y)).toBeLessThanOrEqual(1.0001);
      });
    }
    expect(() => yearShare('heat', 1990)).toThrow();
  });
  it('summarises a crop over picked years as lowest and highest', () => {
    const years = [2005, 2010, 2020];
    const r = cropShareRange('cc1_peanut', 'heat', years);
    const vals = years.map((y) => cropShare('cc1_peanut', 'heat', y));
    expect(r).toEqual({ min: Math.min(...vals), max: Math.max(...vals), count: 3 });
    expect(cropShareRange('cc1_peanut', 'heat', [])).toBeNull();
  });
  it('gives soil wetness between 0 and 1 with a normal', () => {
    const s = soilReading('cc5_rice', [2000, 2020]);
    expect(s?.values.every((v) => v >= 0 && v <= 1)).toBe(true);
    expect(s?.normal).toBeGreaterThan(0);
  });
});

describe('rice history and model gates', () => {
  it('never shows a spring prediction (the spring model failed its test)', () => {
    expect(seasonStatus('spring')).toBe('not_shown');
    for (const y of YEARS) expect(riceYear('spring', y).predicted).toBeNull();
  });
  it('shows winter predictions only for the test years', () => {
    expect(seasonStatus('winter')).toBe('shown');
    for (const y of YEARS) {
      const r = riceYear('winter', y);
      if (y < model.test_years.first) expect(r.predicted).toBeNull();
    }
    expect(riceYear('winter', 2020).predicted).not.toBeNull();
  });
  it('summarises from two years with a value, else lists them', () => {
    expect(riceSummary('spring', [2010]).min).toBeUndefined();
    const s = riceSummary('spring', [2003, 2010, 2020]);
    expect(s.min?.actual).toBeLessThanOrEqual(s.max?.actual as number);
    expect(riceSummary('spring', [1995, 1996]).years).toHaveLength(0); // no normal for the first years
  });
});

describe('farmer state in the URL', () => {
  it('round-trips and drops unknown values', () => {
    const p = new URLSearchParams('ruong=dry&nam=2020,2010,1800,2010&uutien=water&the=cc3');
    const s = parseFarmerState(p);
    expect(s).toEqual({ land: 'water_short', years: [2010, 2020], priority: 'water', plan: 'cc3' });
    expect(parseFarmerState(serializeFarmerState(s))).toEqual(s);
    expect(parseFarmerState(new URLSearchParams('ruong=lake&uutien=gold&the=cc9')).land).toBeNull();
  });
  it('caps the number of picked years', () => {
    let years: number[] = [];
    for (const y of YEARS) years = toggleYear(years, y);
    expect(years).toHaveLength(MAX_YEARS);
    expect(toggleYear([2010, 2020], 2010)).toEqual([2020]);
  });
  // D-169, UI-UX-SPEC section 7: the farmer picks every year; none is picked for them
  it('picks no year by default', () => {
    expect(parseFarmerState(new URLSearchParams('ruong=canal_end')).years).toEqual([]);
    expect(parseFarmerState(new URLSearchParams('nam=')).years).toEqual([]);
  });
  it('keeps the shared plan id of the api', () => {
    expect(parseFarmerState(new URLSearchParams('the=usual_p03')).plan).toBe('usual_p03');
  });
  // UI-UX-SPEC section 7: the dry answer carries the words cao cưỡng, cuối kênh, thiếu nước; section 6b rule 4: an
  // irrigated field gets no compare request
  it('builds the compare body from the answers', () => {
    const base = { years: [2010, 2020], priority: 'water' as const, plan: null };
    for (const land of ['high_field', 'canal_end', 'water_short'] as const) {
      expect(compareRequest({ ...base, land })).toEqual({
        province: 'nghe_an',
        land: 'dry',
        years: [2010, 2020],
        priority: 'water',
      });
    }
    expect(compareRequest({ ...base, land: 'ask' })?.land).toBe('unsure');
    expect(compareRequest({ ...base, land: 'reliable' })).toBeNull();
    expect(compareRequest({ ...base, land: null })).toBeNull();
    expect(compareRequest({ ...base, land: 'ask', priority: null })).toBeNull();
    expect(compareRequest({ ...base, land: 'ask', years: [] })).toBeNull();
  });
});

describe('source registry', () => {
  it('has bilingual text for every field', () => {
    for (const s of Object.values(SOURCES)) {
      for (const field of [s.title, s.publisher, s.where, s.period, s.method, s.howRead, s.caveat]) {
        expect(field.vi.length).toBeGreaterThan(0);
        expect(field.en.length).toBeGreaterThan(0);
      }
    }
  });
});

// UI-UX-SPEC section 9a: lanes keep overlapping spans visible; a bare period whose from is later than to wraps across
// 31 December and is drawn as two pieces; section 6d: "01-17" is shown as "17/1"
describe('month bar of an api plan', () => {
  const span = (key: string, from: string, to: string) => ({
    crop_key: key,
    crop_id: 'x',
    crop: { vi: 'x', en: 'x' },
    variety: null,
    season: 'spring' as const,
    sow_from: from,
    sow_to: from,
    harvest_from: to,
    harvest_to: to,
    source_ids: ['R-P02'],
  });
  it('puts overlapping spans on separate lanes', () => {
    const segs = spanSegments([span('a', '01-17', '05-17'), span('b', '05-10', '08-25'), span('c', '09-01', '12-22')]);
    expect(segs.map((x) => x.lane)).toEqual([0, 1, 0]);
    expect(segs[0]?.start).toBeCloseTo(16 / 365);
    expect(segs[0]?.end).toBeCloseTo(137 / 365);
  });
  it('skips spans without dates', () => {
    expect(
      spanSegments([
        { ...span('a', '01-17', '05-17'), sow_from: null, sow_to: null, harvest_from: null, harvest_to: null },
      ]),
    ).toEqual([]);
  });
  it('splits a period that wraps across the year end', () => {
    expect(periodPieces({ from: '12-11', to: '01-16' })).toEqual([
      { start: 344 / 365, end: 1 },
      { start: 0, end: 16 / 365 },
    ]);
    expect(periodPieces({ from: '05-18', to: '06-05' })).toEqual([{ start: 137 / 365, end: 156 / 365 }]);
  });
  it('writes a date range as day/month', () => {
    expect(dateRange('01-17', '01-18')).toBe('17/1–18/1');
    expect(dateRange('05-17', '05-17')).toBe('17/5');
  });
});
