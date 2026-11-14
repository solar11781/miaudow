// Climate intelligence (AI core 01) as the canonical build writes it: NASA POWER daily values aggregated to complete
// months only (a month with a missing day is null), farmland-weighted over the five Nghệ An cells, against the
// 1991-2020 monthly normal. Grid values from a reanalysis model, never measured on a farm, never a forecast.
import climateJson from '@data/climate.json';

export interface ClimateYear {
  monthly_rain_mm: (number | null)[];
  anomaly_mm: (number | null)[];
  anomaly_pct: (number | null)[];
  annual_rain_mm: number | null;
  hot_days: number | null;
  cold_days: number | null;
  longest_dry_spell_days: number | null;
  drought_rain_months: number[];
}

interface ClimateFile {
  generated_at: string;
  dataset_id: string;
  source_revision: string;
  is_forecast: false;
  is_field_measurement: false;
  years: number[];
  baseline_years: [number, number];
  thresholds: Record<string, number>;
  normal_mm: { farmland_weighted: number[] };
  series: { farmland_weighted: Record<string, ClimateYear> };
}

export const CLIMATE = climateJson as unknown as ClimateFile;
export const CLIMATE_YEARS = CLIMATE.years;
export const climateYear = (y: number): ClimateYear | undefined => CLIMATE.series.farmland_weighted[String(y)];
