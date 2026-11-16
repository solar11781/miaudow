import type { Plan, PlanCrop } from './plans';
import type { CropSpan, Period } from '../types';

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

export const formatDayMonth = (mmdd: string) => {
  const [m, d] = mmdd.split('-');
  return `${Number(d)}/${Number(m)}`;
};

export interface SpanSegment {
  span: CropSpan;
  start: number;
  end: number;
  lane: number;
}

/** Lanes for the API calendar (UI-UX-SPEC section 9a): a span runs from sow_from to harvest_to, drawn as given, and a
 * span that overlaps an earlier one goes on the next free lane. Spans without dates (P-03) are not drawn. */
export function spanSegments(calendar: CropSpan[]): SpanSegment[] {
  const laneEnds: number[] = [];
  return calendar.flatMap((span) => {
    if (span.sow_from === null || span.harvest_to === null) return [];
    const s = dayOfYear(span.sow_from);
    const e = dayOfYear(span.harvest_to);
    let lane = laneEnds.findIndex((end) => end < s);
    if (lane === -1) lane = laneEnds.length;
    laneEnds[lane] = e;
    return [{ span, start: (s - 1) / 365, end: e / 365, lane }];
  });
}

/** A bare period as fractions of the year; one that wraps across 31 December is two pieces. */
export function periodPieces(p: Period): { start: number; end: number }[] {
  const a = dayOfYear(p.from);
  const b = dayOfYear(p.to);
  return a <= b
    ? [{ start: (a - 1) / 365, end: b / 365 }]
    : [
        { start: (a - 1) / 365, end: 1 },
        { start: 0, end: b / 365 },
      ];
}

/** "MM-DD" .. "MM-DD" as day/month, one date when both are the same. */
export const dateRange = (from: string, to: string) =>
  from === to ? formatDayMonth(from) : `${formatDayMonth(from)}–${formatDayMonth(to)}`;
