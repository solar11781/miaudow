// D-185: "I don't remember" picks, for each official hazard, the year it covered the most Nghệ An farmland; on a
// tie the most recent year (easiest to remember). Expected years read from the real past-years data in
// frontend/snapshot/past-years.json (heavy rain 2022, heat 2024, drought 2020 and 2024, damaging cold 2013).
import { describe, expect, it } from 'vitest';
import pastYears from '../../snapshot/past-years.json';
import type { PastYearsResponse } from '../types';
import { hardestYears } from './hardYears';

describe('hardest years', () => {
  it('picks the most recent year of the largest share for each hazard, each year once', () => {
    expect(hardestYears(pastYears as unknown as PastYearsResponse)).toEqual([2013, 2020, 2022, 2024]);
  });
  it('skips a hazard that never happened and a year without a value', () => {
    const res = {
      rules: [{ code: 'heat' }, { code: 'cold' }],
      years: [
        { year: 2001, shares: { heat: { value: '40' }, cold: { value: '0' } } },
        { year: 2002, shares: { heat: null, cold: { value: '0' } } },
        { year: 2003, shares: { heat: { value: '40' }, cold: null } },
      ],
    } as unknown as PastYearsResponse;
    expect(hardestYears(res)).toEqual([2003]);
  });
});
