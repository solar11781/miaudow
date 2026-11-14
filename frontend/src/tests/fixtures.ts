// Contract-shaped test data with placeholder values, as the spec's fixtures use (UI-UX-SPEC section 11).
import { EXPLAIN_KEYS, PLAN_IDS, RULE_CODES, type CompareRequest } from '../types';

export const text = { vi: 'x', en: 'x' };
export const facts = (id: string) => ({
  id,
  citation: text,
  study_type: text,
  place_years: text,
  read_status: null,
  full_text_read: null,
  limitations: [],
  url: null,
  nso_credit: false,
});
export const value = (ids = ['R-N01']) => ({ value: 'xx', unit: text, source_ids: ids });
export const shares = () => Object.fromEntries(RULE_CODES.map((r) => [r, value()]));
export const rule = (code: string) => ({
  code,
  label: text,
  rule_text: text,
  threshold_source_id: 'R-A01',
  values_source_ids: ['R-N01'],
  computed_by: 'E-019',
});
export const sources = {
  'R-A01': facts('R-A01'),
  'R-N01': facts('R-N01'),
  'E-019': facts('E-019'),
  'R-P02': facts('R-P02'),
};

export const pastYears = () => ({
  province: 'nghe_an',
  rules: RULE_CODES.map(rule),
  years: [
    { year: 1995, shares: shares() },
    { year: 1996, shares: { ...shares(), cold: null } },
  ],
  sources,
  n_cells: 5,
});

export const body: CompareRequest = { province: 'nghe_an', land: 'dry', years: [2010, 2020], priority: 'income' };
export const land = { value: value(), principle_source_ids: ['R-P02'] };
export const plan = (id: string) => ({
  id,
  name: text,
  is_usual: id.startsWith('usual'),
  calendar: [
    {
      crop_key: `${id}_spring_rice`,
      crop_id: 'rice',
      crop: text,
      variety: null,
      season: 'spring',
      sow_from: '02-01',
      sow_to: '02-01',
      harvest_from: '05-01',
      harvest_to: '05-01',
      source_ids: ['R-P02'],
    },
  ],
  bare_periods: [{ from: '05-02', to: '01-31' }],
  money: { items: [], total: null, price_year: null, definition: text, text_only: null },
  exposure: [
    {
      crop_key: `${id}_spring_rice`,
      crop: text,
      per_year: body.years.map((year) => ({ year, shares: shares(), soil_wetness: { value: value(), normal: null } })),
    },
  ],
  stability: [
    {
      crop_key: `${id}_spring_rice`,
      season: 'spring',
      label: text,
      model_status: 'not_shown',
      years_count: 2,
      scope: text,
      per_year: body.years.map((year) => ({ year, real: value(), oos_prediction: null, range_80: null })),
      summary: { min: value(), median: value(), max: value() },
      worst_years: [2010],
    },
  ],
  water: [{ crop_key: `${id}_spring_rice`, measure: 'not_listed', value: null, scope: null, note: null }],
  land: {
    crops_in_year: land,
    living_days: land,
    legume: { present: false, crops: [], principle_source_ids: ['R-P02'] },
  },
  why: { why: text, evidence: text, benefits: text, gaps: text, risks: [{ text, source_ids: [] }] },
});
export const compare = () => ({
  request: { ...body },
  test_years: { first: 2016, last: 2024 },
  n_cells: 5,
  seasons: [{ code: 'spring', label: text, window: text, source_ids: ['R-P02'] }],
  rules: RULE_CODES.map(rule),
  gates: [],
  plans: PLAN_IDS.map(plan),
  sources,
});
export const method = () => ({
  test_years: { first: 2016, last: 2024 },
  freeze_commit: 'x',
  metrics: [],
  gates: [],
  weather_claims: [],
  reports: [],
  coverage: [{ row_key: 'r', crop: text, axis: 'money', text, source_ids: ['R-P02'] }],
  explain_terms: EXPLAIN_KEYS.map((key) => ({ key, title: text, text, source_ids: ['R-P02'] })),
  limitations: [text],
  datasets_not_used: [{ dataset: 'x', reason: text, source_ids: ['R-P02'] }],
  rain_check: null,
  sources,
});
