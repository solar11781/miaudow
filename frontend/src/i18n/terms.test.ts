import { describe, expect, it } from 'vitest';
import rotationsJson from '@data/rotations.generated.json';
import { en } from './en';
import { vi } from './vi';

// F9, D-187 item 1: money shows in one unit everywhere, the unit of the plans page. The plans page shows the API's
// money values, whose unit is the P-02 unit of rules/rotations.yaml (also in data/canonical/rotations.generated.json);
// prices use its price_unit {vi: "đồng/kg", en: "đ/kg"} (rules/rotations.yaml, p02_price_unit).
const perHa = rotationsJson.plans.flatMap((p) => (p.reported_economics.unit ? [p.reported_economics.unit] : []));
const PER_HA = { vi: perHa[0]?.vi, en: perHa[0]?.en };
const PER_KG = { vi: 'đồng/kg', en: 'đ/kg' };

// Other spellings of the same units that the plans page never shows.
const OTHER_SPELLINGS = { vi: [/nghìn đ\/ha/, /\sđ\/kg/], en: [/thousand VND\/ha/, /VND\/kg/] };

const sources = import.meta.glob<string>(['./vi.ts', './en.ts'], { query: '?raw', import: 'default', eager: true });

describe('one money unit (F9)', () => {
  it('every plan in the API data has the same money unit', () => {
    expect(new Set(perHa.map((u) => `${u.vi}|${u.en}`)).size).toBe(1);
  });

  it('the shared unit texts are the plans page units', () => {
    expect(vi.common.thousandPerHa).toBe(PER_HA.vi);
    expect(en.common.thousandPerHa).toBe(PER_HA.en);
    expect(vi.common.perKg).toBe(PER_KG.vi);
    expect(en.common.perKg).toBe(PER_KG.en);
  });

  it('the text files spell the thousand and price units only one way', () => {
    // the million unit (common.millionPerHa) stays until HomePage.tsx and claims.ts (open PRs) show thousands
    const vis = sources['./vi.ts'] ?? '';
    const ens = sources['./en.ts'] ?? '';
    expect(vis.length).toBeGreaterThan(0);
    for (const re of OTHER_SPELLINGS.vi) expect(vis, String(re)).not.toMatch(re);
    for (const re of OTHER_SPELLINGS.en) expect(ens, String(re)).not.toMatch(re);
  });
});
