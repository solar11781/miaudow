import { YEARS } from '../data';
import { PLAN_IDS, type CompareRequest, type PlanId } from '../types';

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

// UI-UX-SPEC section 7: the three water-short answers are the land type "dry" (cao cưỡng, cuối kênh, thiếu nước); not
// sure is "unsure"; an irrigated field gets no compare request (section 6b rule 4)
const API_LAND: Record<Land, CompareRequest['land'] | null> = {
  high_field: 'dry', canal_end: 'dry', water_short: 'dry', ask: 'unsure', reliable: null,
};

/** The POST /api/compare body from the answers, or null while an answer is missing or the field is irrigated. */
export function compareRequest(s: FarmerState): CompareRequest | null {
  const land = s.land ? API_LAND[s.land] : null;
  if (!land || !s.priority || !s.years.length) return null;
  return { province: 'nghe_an', land, years: s.years, priority: s.priority };
}
