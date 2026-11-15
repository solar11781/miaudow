import type { PastYearsResponse } from '../types';
import { MAX_YEARS } from './farmerState';

/** D-185: for each official hazard, the year it covered the most farmland (the most recent on a tie, the easiest to
 * remember); a hazard that never happened adds no year. Each year once, in order. */
export function hardestYears(res: PastYearsResponse): number[] {
  const picked = new Set<number>();
  for (const rule of res.rules) {
    let best: { year: number; share: number } | null = null;
    for (const row of res.years) {
      const v = row.shares[rule.code];
      if (!v) continue;
      const share = Number(v.value);
      if (share > 0 && (!best || share > best.share || (share === best.share && row.year > best.year)))
        best = { year: row.year, share };
    }
    if (best) picked.add(best.year);
  }
  return [...picked].sort((a, b) => a - b).slice(0, MAX_YEARS);
}
