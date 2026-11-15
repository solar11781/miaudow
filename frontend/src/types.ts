// The data contract of UI-UX-SPEC section 11, names and fields exactly as there (mirrored by
// src/fieldshift/engine/schemas.py).

export type Lang = 'vi' | 'en';
export type Text = Record<Lang, string>;
export type Province = 'nghe_an';
export type Land = 'dry' | 'unsure';
export type Priority = 'income' | 'stability' | 'water' | 'land';
export type PlanId = 'usual' | 'usual_p03' | 'cc1' | 'cc2' | 'cc3' | 'cc4';
export type SeasonCode = 'spring' | 'summer_autumn' | 'winter' | 'autumn_winter';
export type RuleCode = 'heavy_rain' | 'heat' | 'drought_rain_consecutive' | 'drought_rain_any2' | 'cold';
export type SourceId = string;

export const RULE_CODES: readonly RuleCode[] = [
  'heavy_rain',
  'heat',
  'drought_rain_consecutive',
  'drought_rain_any2',
  'cold',
];
export const PLAN_IDS: readonly PlanId[] = ['usual', 'usual_p03', 'cc1', 'cc2', 'cc3', 'cc4'];
export const SEASON_CODES: readonly SeasonCode[] = ['spring', 'summer_autumn', 'winter', 'autumn_winter'];

export interface SourceFacts {
  id: SourceId;
  citation: Text;
  study_type: Text;
  place_years: Text;
  read_status: string | null;
  full_text_read: boolean | null;
  limitations: Text[];
  url: string | null;
  nso_credit: boolean;
}

export interface Value {
  value: string;
  unit: Text;
  source_ids: SourceId[];
}
export interface Season {
  code: SeasonCode;
  label: Text;
  window: Text;
  source_ids: SourceId[];
}
export interface Rule {
  code: RuleCode;
  label: Text;
  rule_text: Text;
  threshold_source_id: SourceId;
  values_source_ids: SourceId[];
  computed_by: SourceId;
}
export interface YearRow {
  year: number;
  shares: Record<RuleCode, Value | null>;
}

export interface PastYearsResponse {
  province: Province;
  rules: Rule[];
  years: YearRow[];
  sources: Record<SourceId, SourceFacts>;
  n_cells: number;
}

export interface CropSpan {
  crop_key: string;
  crop_id: string;
  crop: Text;
  variety: Text | null;
  season: SeasonCode;
  sow_from: string | null;
  sow_to: string | null;
  harvest_from: string | null;
  harvest_to: string | null;
  source_ids: SourceId[];
}
export interface Period {
  from: string;
  to: string;
}
export interface MoneyItem {
  crop_key: string;
  crop: Text;
  season: SeasonCode;
  profit: Value;
  cost: Value | null;
  /** The study's yield and sale price of the crop (UI-UX-SPEC section 12d, D-163). */
  yield: Value;
  price: Value;
  flag: Text | null;
}
/** One season's money as the study writes it (D-191, P-03): its value, or null where the study gives none. */
export interface SeasonValue {
  season: SeasonCode;
  value: Value | null;
  page: string;
  words: Text;
}
export interface Money {
  items: MoneyItem[];
  total: Value | null;
  price_year: string | null;
  definition: Text;
  season_values: SeasonValue[];
}
export interface CropExposure {
  crop_key: string;
  crop: Text;
  per_year: {
    year: number;
    shares: Record<RuleCode, Value | null>;
    soil_wetness: { value: Value | null; normal: Value | null };
  }[];
}
export interface StabilityYear {
  year: number;
  real: Value | null;
  oos_prediction: Value | null;
  range_80: { low: Value; high: Value } | null;
}
export type ModelStatus = 'shown' | 'not_shown' | 'not_modeled';
export interface Stability {
  crop_key: string;
  season: SeasonCode;
  label: Text;
  model_status: ModelStatus;
  years_count: number;
  scope: Text;
  per_year: StabilityYear[];
  summary: { min: Value; median: Value; max: Value } | null;
  worst_years: number[];
}
export interface WaterFact {
  crop_key: string;
  measure: 'to_apply' | 'crop_uses' | 'not_listed';
  value: Value | null;
  scope: Text | null;
  note: Text | null;
}
export interface LandCheck {
  value: Value | null;
  principle_source_ids: SourceId[];
}
export interface LandCare {
  crops_in_year: LandCheck;
  living_days: LandCheck;
  legume: { present: boolean; crops: Text[]; principle_source_ids: SourceId[] };
}
export interface RiskItem {
  text: Text;
  source_ids: SourceId[];
}
export interface Why {
  why: Text;
  evidence: Text;
  benefits: Text;
  gaps: Text;
  risks: RiskItem[];
}

export interface Plan {
  id: PlanId;
  name: Text;
  is_usual: boolean;
  calendar: CropSpan[];
  bare_periods: Period[];
  money: Money;
  exposure: CropExposure[];
  stability: Stability[] | null;
  water: WaterFact[];
  land: LandCare;
  why: Why;
}

export interface CompareRequest {
  province: Province;
  land: Land;
  years: number[];
  priority: Priority;
}
export interface Interval {
  value: number;
  ci90_low: number;
  ci90_high: number;
}
export interface GateRow {
  gate: 'G1' | 'G2' | 'G3' | 'G4';
  season: SeasonCode;
  model_id: string | null;
  passed: boolean | null;
  detail: Text;
  source_ids: SourceId[];
}

export interface CompareResponse {
  request: CompareRequest;
  test_years: { first: number; last: number };
  n_cells: number;
  seasons: Season[];
  rules: Rule[];
  gates: GateRow[];
  plans: Plan[];
  sources: Record<SourceId, SourceFacts>;
}

export type ModelId = 'b0' | 'b2' | 'bnw' | 'm1_ridge' | 'm2_lgbm' | 'm3_rf';
export type Sensitivity = 'no_fao_flagged' | 'mae_skill' | 'risk_level_features' | 'window' | 'centroid_points';
export interface MetricRow {
  model_id: ModelId;
  season: SeasonCode;
  role: 'primary' | 'secondary' | 'reference';
  scheme: 'rolling_origin' | 'spatial_holdout';
  sensitivity: Sensitivity | null;
  detail: Text | null;
  subset: string;
  rmse: number | null;
  mae: number | null;
  r2_oos: number | null;
  skill_vs_b0: Interval | null;
  skill_vs_b2: Interval | null;
  skill_vs_bnw: Interval | null;
  coverage_80: number | null;
  n_rows: number;
  n_test_years: number;
  source_ids: SourceId[];
}
export interface WeatherClaim {
  season: SeasonCode;
  model_id: ModelId;
  made: boolean;
  source_ids: SourceId[];
}
export interface ReportItem {
  id: SourceId;
  title: Text;
  text: Text;
  source_ids: SourceId[];
}
export type CoverageAxis = 'money' | 'conditions' | 'rice_history' | 'model' | 'water_tcvn' | 'water_fao';
export interface CoverageCell {
  row_key: string;
  crop: Text;
  axis: CoverageAxis;
  text: Text;
  source_ids: SourceId[];
}
export type ExplainKey = 'evapotranspiration' | 'soil_moisture' | 'ndvi' | 'frost' | 'water_balance' | 'data_types';
export interface ExplainTerm {
  key: ExplainKey;
  title: Text;
  text: Text;
  source_ids: SourceId[];
}
export interface NotUsedDataset {
  dataset: string;
  reason: Text;
  source_ids: SourceId[];
}
export interface RainCheck {
  months: { month: string; imerg: Value; power: Value }[];
  cc: Value;
  mean_imerg: Value;
  mean_power: Value;
  source_ids: SourceId[];
}
export interface MethodResponse {
  test_years: { first: number; last: number };
  freeze_commit: string;
  metrics: MetricRow[];
  gates: GateRow[];
  weather_claims: WeatherClaim[];
  reports: ReportItem[];
  coverage: CoverageCell[];
  explain_terms: ExplainTerm[];
  limitations: Text[];
  datasets_not_used: NotUsedDataset[];
  /** The sources of the PICSA sentence, whose text is the key method.picsa (UI-UX-SPEC section 11b item 5). */
  picsa: { source_ids: SourceId[] };
  rain_check: RainCheck | null;
  sources: Record<SourceId, SourceFacts>;
}

export const COVERAGE_AXES: readonly CoverageAxis[] = [
  'money',
  'conditions',
  'rice_history',
  'model',
  'water_tcvn',
  'water_fao',
];
export const EXPLAIN_KEYS: readonly ExplainKey[] = [
  'evapotranspiration',
  'soil_moisture',
  'ndvi',
  'frost',
  'water_balance',
  'data_types',
];
