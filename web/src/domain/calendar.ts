import type { Plan, PlanCrop } from './plans';

// Calendar arithmetic on a non-leap reference year. Dates are MM-DD as reported by the trial.
const MONTH_START = [0, 31, 59, 90, 120, 151, 181, 212, 243, 273, 304, 334];

export function dayOfYear(mmdd: string): number {
  const [m, d] = mmdd.split('-').map(Number);
  if (!m || !d || m < 1 || m > 12 || d < 1 || d > 31) throw new Error(`invalid MM-DD: ${mmdd}`);
  return (MONTH_START[m - 1] ?? 0) + d;
}

export interface Segment {
  crop: PlanCrop;
  /** Fraction of the year, 0..1. */
  start: number;
  end: number;
  lane: number;
}

/** Bar segments with lanes, so overlapping reported dates are shown side by side instead of hidden. */
export function segments(plan: Plan): Segment[] {
  const sorted = [...plan.crops].sort((a, b) => dayOfYear(a.sow) - dayOfYear(b.sow));
  const laneEnds: number[] = [];
  return sorted.map((crop) => {
    const s = dayOfYear(crop.sow);
    const e = dayOfYear(crop.harvest);
    let lane = laneEnds.findIndex((end) => end < s);
    if (lane === -1) lane = laneEnds.length;
    laneEnds[lane] = e;
    return { crop, start: (s - 1) / 365, end: e / 365, lane };
  });
}

/** Days with a living crop out of 365: the union of field days, both ends included. */
export function livingDays(plan: Plan): number {
  const days = new Set<number>();
  for (const c of plan.crops) for (let d = dayOfYear(c.sow); d <= dayOfYear(c.harvest); d++) days.add(d);
  return days.size;
}

/** Calendar months (1..12) without any field day. */
export function bareMonths(plan: Plan): number[] {
  if (!plan.crops.length) return [];
  const used = new Set<number>();
  for (const c of plan.crops) {
    const a = dayOfYear(c.sow);
    const b = dayOfYear(c.harvest);
    MONTH_START.forEach((start, i) => {
      const end = (MONTH_START[i + 1] ?? 365);
      if (a <= end && b > start) used.add(i + 1);
    });
  }
  return Array.from({ length: 12 }, (_, i) => i + 1).filter((m) => !used.has(m));
}

export const formatDayMonth = (mmdd: string) => {
  const [m, d] = mmdd.split('-');
  return `${Number(d)}/${Number(m)}`;
};
