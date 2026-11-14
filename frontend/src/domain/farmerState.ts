import { YEARS } from '../data';
import { PLAN_IDS, type CompareRequest, type PlanId } from '../types';
import { readWhole } from './ownMoney';

/** The farmer's water situation, the same ids the API's decision core uses; 'ask' = not sure. */
export type Land = 'high_field' | 'canal_end' | 'water_short' | 'reliable' | 'ask';
export type Priority = 'income' | 'stability' | 'water' | 'land';

export interface FarmerState {
  land: Land | null;
  years: number[];
  priority: Priority | null;
  plan: PlanId | null;
  own: OwnNumbers;
}

/** "Your price and costs" by crop key, as digits (UI-UX-SPEC section 12d): prices in đ/kg, costs in thousand đ/ha. */
export interface OwnNumbers {
  prices: Record<string, string>;
  costs: Record<string, string>;
}
export const NO_OWN: OwnNumbers = { prices: {}, costs: {} };
// fragment keys yp.<crop key> and yc.<crop key> (research/price-entry-notes.md section 5, D-163)
const OWN_KEY = /^y([pc])\.([a-z0-9_]+)$/;
/** A fragment key of the farmer's own price or cost. */
export const isOwnKey = (key: string) => OWN_KEY.test(key);

export const LANDS: Land[] = ['high_field', 'canal_end', 'water_short', 'reliable', 'ask'];
/** Links shared before the four water situations existed keep working. */
const LEGACY_LAND: Record<string, Land> = { dry: 'water_short', wet: 'reliable' };
const PRIORITIES: Priority[] = ['income', 'stability', 'water', 'land'];
const MAX_YEARS = 10;

const pick = <T extends string>(allowed: readonly T[], raw: string | null): T | null =>
  raw && (allowed as readonly string[]).includes(raw) ? (raw as T) : null;

/** Reads the shareable state from URL search params; anything unknown is dropped, never guessed. */
export function parseFarmerState(params: URLSearchParams): FarmerState {
  // no year is picked for the farmer (D-169)
  const years = [
    ...new Set(
      (params.get('nam') ?? '')
        .split(',')
        .map(Number)
        .filter((y) => YEARS.includes(y)),
    ),
  ]
    .sort((a, b) => a - b)
    .slice(0, MAX_YEARS);
  return {
    land: pick(LANDS, params.get('ruong')) ?? LEGACY_LAND[params.get('ruong') ?? ''] ?? null,
    years,
    priority: pick(PRIORITIES, params.get('uutien')),
    plan: pick(PLAN_IDS, params.get('the')),
    own: parseOwn(params),
  };
}

function parseOwn(params: URLSearchParams): OwnNumbers {
  const own: OwnNumbers = { prices: {}, costs: {} };
  for (const [key, raw] of params) {
    const m = OWN_KEY.exec(key);
    const digits = readWhole(raw);
    if (m?.[2] && typeof digits === 'string' && digits !== 'invalid')
      own[m[1] === 'p' ? 'prices' : 'costs'][m[2]] = digits;
  }
  return own;
}

/** `own` with one crop's price or cost set to `digits`, or removed when null. */
export function setOwn(own: OwnNumbers, field: keyof OwnNumbers, crop: string, digits: string | null): OwnNumbers {
  const next = Object.fromEntries(Object.entries(own[field]).filter(([k]) => k !== crop));
  if (digits !== null) next[crop] = digits;
  return { ...own, [field]: next };
}

/** Only the crop keys of the compare response (UI-UX-SPEC section 6b rule 2: unknown keys are dropped). */
export function ownOf(own: OwnNumbers, cropKeys: string[]): OwnNumbers {
  const keep = (m: Record<string, string>) =>
    Object.fromEntries(Object.entries(m).filter(([k]) => cropKeys.includes(k)));
  return { prices: keep(own.prices), costs: keep(own.costs) };
}

export function serializeFarmerState(s: FarmerState): URLSearchParams {
  const p = new URLSearchParams();
  if (s.land) p.set('ruong', s.land);
  p.set('nam', s.years.join(','));
  if (s.priority) p.set('uutien', s.priority);
  if (s.plan) p.set('the', s.plan);
  for (const [crop, digits] of Object.entries(s.own.prices)) p.set(`yp.${crop}`, digits);
  for (const [crop, digits] of Object.entries(s.own.costs)) p.set(`yc.${crop}`, digits);
  return p;
}

export const toggleYear = (years: number[], year: number) =>
  years.includes(year) ? years.filter((y) => y !== year) : [...years, year].sort((a, b) => a - b).slice(-MAX_YEARS);

export { MAX_YEARS };

// UI-UX-SPEC section 7: the three water-short answers are the land type "dry" (cao cưỡng, cuối kênh, thiếu nước); not
// sure is "unsure"; an irrigated field gets no compare request (section 6b rule 4)
const API_LAND: Record<Land, CompareRequest['land'] | null> = {
  high_field: 'dry',
  canal_end: 'dry',
  water_short: 'dry',
  ask: 'unsure',
  reliable: null,
};

/** The POST /api/compare body from the answers, or null while an answer is missing or the field is irrigated. */
export function compareRequest(s: Pick<FarmerState, 'land' | 'years' | 'priority'>): CompareRequest | null {
  const land = s.land ? API_LAND[s.land] : null;
  if (!land || !s.priority || !s.years.length) return null;
  return { province: 'nghe_an', land, years: s.years, priority: s.priority };
}
