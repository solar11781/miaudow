import { model, yearIndex, type RiceSeason } from '../data';

export interface RiceYear {
  year: number;
  /** Real NSO anomaly (actual / normal − 1), or null when no normal exists. */
  actual: number | null;
  /** Out-of-sample model value, only for 2016–2024 and only when the season's own test passed. */
  predicted: number | null;
  low80: number | null;
  high80: number | null;
}

export const seasonStatus = (season: RiceSeason) =>
  model.seasons.find((s) => s.season === season)?.model_status ?? 'not_modeled';

export function riceYear(season: RiceSeason, year: number): RiceYear {
  const h = model.history[season];
  const i = yearIndex(year);
  const shown = seasonStatus(season) === 'shown' && year >= model.test_years.first && year <= model.test_years.last;
  return {
    year,
    actual: h.anom_history[i] ?? null,
    predicted: shown ? (h.anom_oos[i] ?? null) : null,
    low80: shown ? (h.oos_low_80[i] ?? null) : null,
    high80: shown ? (h.oos_high_80[i] ?? null) : null,
  };
}

export interface RiceSummary {
  /** Years with a real value, in the picked order. */
  years: RiceYear[];
  min?: RiceYear;
  max?: RiceYear;
  median?: number;
}

/**
 * Lowest / middle / highest of the real values with the worst year named, from 2 picked years with a value on
 * (with fewer, each year is shown on its own). No percentile band: a handful of years cannot support one.
 */
export function riceSummary(season: RiceSeason, picked: number[]): RiceSummary {
  const years = picked.map((y) => riceYear(season, y)).filter((r) => r.actual !== null);
  if (years.length < 2) return { years };
  const sorted = [...years].sort((a, b) => (a.actual as number) - (b.actual as number));
  const mid = sorted.length / 2;
  const vals = sorted.map((r) => r.actual as number);
  const median =
    sorted.length % 2 ? (vals[Math.floor(mid)] as number) : ((vals[mid - 1] as number) + (vals[mid] as number)) / 2;
  return { years, min: sorted[0], max: sorted[sorted.length - 1], median };
}
