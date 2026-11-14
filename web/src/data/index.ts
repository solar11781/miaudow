// Typed access to the generated data files (pipeline/build_data.py, pipeline/build_photos.mjs). Values are not changed.
import geoJson from './generated/geo.json';
import hazardsJson from './generated/hazards.json';
import modelJson from './generated/model.json';
import photosJson from './generated/photos.json';
import soilJson from './generated/soil.json';

export type RuleCode = 'heavy_rain' | 'heat' | 'drought_rain_consecutive' | 'drought_rain_any2' | 'cold';
export type Magnitude = 'max_rain_mm' | 'hot_days' | 'cold_days' | 'drought_months';

export interface Cell {
  id: string;
  lat: number;
  lon: number;
  weight: number;
}

export interface HazardData {
  generated_at: string;
  years: number[];
  rules: RuleCode[];
  cells: Cell[];
  year_months: number[];
  crops: Record<string, { sow: string; harvest: string }>;
  year_level: Record<RuleCode, number[]>;
  crop_level: Record<string, Record<RuleCode, number[]>>;
  cell_level: Record<RuleCode, Record<string, boolean[]>>;
  magnitudes: Record<Magnitude, Record<string, number[]>>;
}

export interface SoilData {
  generated_at: string;
  years: number[];
  crops: Record<string, { values: number[]; normal_1991_2020: number }>;
}

export interface GeoData {
  outline: [number, number][][];
  grid: (Cell & { inside_share: number })[];
  bounds: [number, number, number, number];
}

export type RiceSeason = 'spring' | 'summer_autumn' | 'winter';

export interface SkillValue {
  value: number;
  ci90_low: number;
  ci90_high: number;
}

export interface MetricRow {
  model_id: 'b0' | 'b2' | 'bnw' | 'm1_ridge' | 'm2_lgbm' | 'm3_rf';
  season: RiceSeason;
  role: string;
  scheme: 'rolling_origin' | 'spatial_holdout';
  subset: string;
  mae: number;
  rmse: number;
  r2_oos: number;
  skill_vs_b0: SkillValue | null;
  skill_vs_b2: SkillValue | null;
  skill_vs_bnw: SkillValue | null;
  coverage_80: number | null;
  n_rows: number;
  n_test_years: number;
}

export interface Gate {
  gate: 'G1' | 'G2' | 'G3' | 'G4';
  season: RiceSeason;
  model_id: string | null;
  passed: boolean;
  detail: { vi: string; en: string };
}

export interface ModelData {
  generated_at: string;
  years: number[];
  freeze_commit: string;
  test_years: { first: number; last: number };
  seasons: { season: RiceSeason; model_status: 'shown' | 'not_shown' | 'not_modeled'; model_id: string | null }[];
  history: Record<RiceSeason, { anom_history: (number | null)[]; anom_oos: (number | null)[]; oos_low_80: (number | null)[]; oos_high_80: (number | null)[] }>;
  metrics: MetricRow[];
  gates: Gate[];
  weather_claims: { season: RiceSeason; model_id: string; made: boolean }[];
  reports: { id: string; title: { vi: string; en: string }; text: { vi: string; en: string } }[];
}

export interface PhotoAsset {
  width: number;
  height: number;
  sources: { w: number; src: string }[];
  placeholder: string;
  dominant: string;
}

export const hazards = hazardsJson as unknown as HazardData;
export const soil = soilJson as unknown as SoilData;
export const geo = geoJson as unknown as GeoData;
export const model = modelJson as unknown as ModelData;
export const photoAssets = photosJson as unknown as Record<string, PhotoAsset>;

export const YEARS = hazards.years;
export const yearIndex = (year: number) => YEARS.indexOf(year);
