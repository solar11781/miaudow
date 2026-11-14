// Climate ML (AI core 01, part two) as the canonical build writes it from api/miaudow_api/climate_ml.py: the three
// closest past years for every year, and an unusual-year score per year, each with its tested verdict. Comparisons of
// past weather on the NASA POWER grid, never a forecast.
import mlJson from '@data/climate_ml.json';
import type { Bilingual } from '../domain/provenance';

export interface FeatureDriver {
  feature: string;
  label: Bilingual;
  unit: string;
  target_value: number | null;
  other_value: number | null;
}

export interface Analog {
  year: number;
  order: number;
  distance: number;
  annual_rain_anomaly_pct: number | null;
  drivers: FeatureDriver[];
}

export interface MonthDriver {
  month: number;
  robust_z: number;
  rain_mm: number;
  baseline_median_mm: number;
  direction: 'drier' | 'wetter';
}

export interface AnomalyYear {
  year: number;
  in_baseline: boolean;
  score: number;
  flagged: boolean;
  driving_months: MonthDriver[];
  annual_rain_mm: number;
  annual_rain_anomaly_pct: number | null;
  percentile_flag: string | null;
}

export interface MethodEvaluation {
  task: Bilingual;
  n_cases: number;
  scores: Record<string, number | null>;
  beats_baselines: boolean;
  verdict: Bilingual;
}

interface ClimateMlFile {
  generated_at: string;
  model_id: string;
  model_version: string;
  baseline_years: [number, number];
  is_forecast: false;
  analogs: {
    median_pairwise_distance: number;
    by_year: Record<string, Analog[]>;
    evaluation: MethodEvaluation;
    limitations: Bilingual[];
  };
  anomalies: {
    threshold: number;
    percentile_bounds_mm: [number, number];
    years: AnomalyYear[];
    evaluation: MethodEvaluation;
    limitations: Bilingual[];
  };
}

export const CLIMATE_ML = mlJson as unknown as ClimateMlFile;
export const analogsOf = (year: number): Analog[] => CLIMATE_ML.analogs.by_year[String(year)] ?? [];
export const anomalyOf = (year: number): AnomalyYear | undefined => CLIMATE_ML.anomalies.years.find((y) => y.year === year);
