import { describe, expect, it } from 'vitest';
import { hazards, model, YEARS } from '../data';
import { bareMonths, dayOfYear, livingDays, segments } from './calendar';
import { cropShare, cropShareRange, RULES, soilReading, yearShare } from './hazards';
import { parseFarmerState, serializeFarmerState, toggleYear, MAX_YEARS } from './farmerState';
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
    for (const p of PLANS) for (const c of p.crops) expect(hazards.crops[c.key]).toEqual({ sow: c.sow, harvest: c.harvest });
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
    expect(s).toEqual({ land: 'dry', years: [2010, 2020], priority: 'water', plan: 'cc3' });
    expect(parseFarmerState(serializeFarmerState(s))).toEqual(s);
    expect(parseFarmerState(new URLSearchParams('ruong=lake&uutien=gold&the=cc9')).land).toBeNull();
  });
  it('caps the number of picked years', () => {
    let years: number[] = [];
    for (const y of YEARS) years = toggleYear(years, y);
    expect(years).toHaveLength(MAX_YEARS);
    expect(toggleYear([2010, 2020], 2010)).toEqual([2020]);
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
