import { YEARS } from '../data';
import type { PlanId } from './plans';

/** The farmer's water situation, the same ids the API's decision core uses; 'ask' = not sure. */
export type Land = 'high_field' | 'canal_end' | 'water_short' | 'reliable' | 'ask';
export type Priority = 'income' | 'stability' | 'water' | 'land';

export interface FarmerState {
  land: Land | null;
  years: number[];
  priority: Priority | null;
  plan: PlanId | null;
}

export const LANDS: Land[] = ['high_field', 'canal_end', 'water_short', 'reliable', 'ask'];
/** Links shared before the four water situations existed keep working. */
const LEGACY_LAND: Record<string, Land> = { dry: 'water_short', wet: 'reliable' };
const PRIORITIES: Priority[] = ['income', 'stability', 'water', 'land'];
const PLAN_IDS: PlanId[] = ['cc5', 'p03', 'cc1', 'cc2', 'cc3', 'cc4'];
const MAX_YEARS = 10;

export const DEFAULT_YEARS = [2010, 2015, 2020];

const pick = <T extends string>(allowed: readonly T[], raw: string | null): T | null =>
  raw && (allowed as readonly string[]).includes(raw) ? (raw as T) : null;

/** Reads the shareable state from URL search params; anything unknown is dropped, never guessed. */
export function parseFarmerState(params: URLSearchParams): FarmerState {
  const rawYears = params.get('nam');
  const years = rawYears === null
    ? DEFAULT_YEARS
    : [...new Set(rawYears.split(',').map(Number).filter((y) => YEARS.includes(y)))].sort((a, b) => a - b).slice(0, MAX_YEARS);
  return {
    land: pick(LANDS, params.get('ruong')) ?? LEGACY_LAND[params.get('ruong') ?? ''] ?? null,
    years,
    priority: pick(PRIORITIES, params.get('uutien')),
    plan: pick(PLAN_IDS, params.get('the')),
  };
}

export function serializeFarmerState(s: FarmerState): URLSearchParams {
  const p = new URLSearchParams();
  if (s.land) p.set('ruong', s.land);
  p.set('nam', s.years.join(','));
  if (s.priority) p.set('uutien', s.priority);
  if (s.plan) p.set('the', s.plan);
  return p;
}

export const toggleYear = (years: number[], year: number) =>
  years.includes(year) ? years.filter((y) => y !== year) : [...years, year].sort((a, b) => a - b).slice(-MAX_YEARS);

export { MAX_YEARS };
