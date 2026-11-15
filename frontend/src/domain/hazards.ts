import { hazards, soil, yearIndex, type Magnitude, type RuleCode } from '../data';
import type { Bilingual } from './provenance';

export interface RuleInfo {
  code: RuleCode;
  name: Bilingual;
  short: Bilingual;
  article: Bilingual;
  quote: string;
  computed: Bilingual;
  magnitude: Magnitude;
  unit: Bilingual;
  /** CSS custom property holding the rule's data colour. */
  color: string;
}

// Quotes are verbatim from QĐ 18/2021/QĐ-TTg; "computed" says what Miaudow does with NASA POWER values.
export const RULES: Record<RuleCode, RuleInfo> = {
  heavy_rain: {
    code: 'heavy_rain',
    name: { vi: 'Mưa lớn', en: 'Heavy rain' },
    short: { vi: 'Mưa lớn', en: 'Rain' },
    article: { vi: 'Điều 44', en: 'Art. 44' },
    quote:
      'lượng mưa từ 100 mm đến 200 mm trong 24 giờ hoặc từ 50 mm đến 100 mm trong 12 giờ, kéo dài từ 1 ngày đến 2 ngày',
    computed: {
      vi: 'Một ngày có lượng mưa từ 100 mm trở lên (không tính được nhánh 12 giờ vì NASA cho số liệu theo ngày).',
      en: 'A day with 100 mm of rain or more (the 12-hour branch is not computable from daily values).',
    },
    magnitude: 'max_rain_mm',
    unit: { vi: 'mm, ngày mưa nhiều nhất', en: 'mm, wettest day' },
    color: 'var(--data-rain)',
  },
  heat: {
    code: 'heat',
    name: { vi: 'Nắng nóng', en: 'Heat' },
    short: { vi: 'Nắng nóng', en: 'Heat' },
    article: { vi: 'Điều 47', en: 'Art. 47' },
    quote: 'đợt nắng nóng với nhiệt độ cao nhất trong ngày từ 35°c đến 37°c, kéo dài từ 3 ngày trở lên',
    computed: {
      vi: 'Từ 3 ngày liền trở lên có nhiệt độ cao nhất nằm trong cùng một bậc nhiệt của Điều 47.',
      en: 'At least 3 consecutive days with the daily maximum inside one band of Art. 47.',
    },
    magnitude: 'hot_days',
    unit: { vi: 'ngày từ 35 °C trở lên', en: 'days at 35 °C or above' },
    color: 'var(--data-heat)',
  },
  drought_rain_any2: {
    code: 'drought_rain_any2',
    name: { vi: 'Hạn hán (phần lượng mưa)', en: 'Drought (rain part)' },
    short: { vi: 'Hạn hán', en: 'Drought' },
    article: { vi: 'Điều 48', en: 'Art. 48' },
    quote: 'thiếu hụt tổng lượng mưa tháng trên 50% so với trung bình nhiều năm, kéo dài từ 2 tháng đến 3 tháng',
    computed: {
      vi: 'Có ít nhất 2 tháng mưa thiếu hơn 50% so với trung bình 1991–2020 của cùng tháng (cách đọc “2 tháng bất kỳ”).',
      en: 'At least 2 months with rain more than 50% below the 1991–2020 mean of that month (“any 2 months” reading).',
    },
    magnitude: 'drought_months',
    unit: { vi: 'tháng thiếu mưa', en: 'dry months' },
    color: 'var(--data-drought)',
  },
  drought_rain_consecutive: {
    code: 'drought_rain_consecutive',
    name: { vi: 'Hạn hán (2 tháng liền)', en: 'Drought (2 months in a row)' },
    short: { vi: 'Hạn hán liền', en: 'Drought+' },
    article: { vi: 'Điều 48', en: 'Art. 48' },
    quote: 'thiếu hụt tổng lượng mưa tháng trên 50% so với trung bình nhiều năm, kéo dài từ 2 tháng đến 3 tháng',
    computed: {
      vi: 'Có 2 tháng liền nhau mưa thiếu hơn 50% so với trung bình 1991–2020 (cách đọc “liên tiếp”).',
      en: 'Two consecutive months with rain more than 50% below the 1991–2020 mean (“consecutive” reading).',
    },
    magnitude: 'drought_months',
    unit: { vi: 'tháng thiếu mưa', en: 'dry months' },
    color: 'var(--data-drought-strong)',
  },
  cold: {
    code: 'cold',
    name: { vi: 'Rét hại', en: 'Damaging cold' },
    short: { vi: 'Rét', en: 'Cold' },
    article: { vi: 'Điều 53', en: 'Art. 53' },
    quote:
      'nhiệt độ không khí trung bình ngày từ trên 8°c đến 13°c, kéo dài từ trên 5 ngày đến 10 ngày ở vùng đồng bằng Bắc Bộ, Bắc Trung Bộ, Trung Trung Bộ',
    computed: {
      vi: 'Ít nhất 6 ngày liền nhiệt độ trung bình trên 8 °C đến 13 °C, hoặc ít nhất 3 ngày liền từ 8 °C trở xuống.',
      en: 'At least 6 consecutive days with mean temperature above 8 °C and up to 13 °C, or at least 3 days at 8 °C or below.',
    },
    magnitude: 'cold_days',
    unit: { vi: 'ngày từ 13 °C trở xuống', en: 'days at 13 °C or below' },
    color: 'var(--data-cold)',
  },
};

/** Rules shown to farmers, in a fixed order (the consecutive drought reading is shown next to "any 2" on the cards). */
export const FARMER_RULES: RuleCode[] = ['drought_rain_any2', 'heat', 'heavy_rain', 'cold'];

const at = (series: number[] | undefined, year: number) => {
  const i = yearIndex(year);
  const v = i < 0 || !series ? undefined : series[i];
  if (v === undefined) throw new Error(`no value for ${year}`);
  return v;
};

/** Share of Nghệ An farmland where the rule was met in the year, over the joined P-02 field time. */
export const yearShare = (rule: RuleCode, year: number) => at(hazards.year_level[rule], year);

/** Share for one P-02 crop over its own field time. */
export const cropShare = (cropKey: string, rule: RuleCode, year: number) =>
  at(hazards.crop_level[cropKey]?.[rule], year);

export interface Range {
  min: number;
  max: number;
  count: number;
}

export function cropShareRange(cropKey: string, rule: RuleCode, years: number[]): Range | null {
  if (!years.length) return null;
  const vals = years.map((y) => cropShare(cropKey, rule, y));
  return { min: Math.min(...vals), max: Math.max(...vals), count: vals.length };
}

export const cellMet = (rule: RuleCode, cellId: string, year: number) => {
  const v = hazards.cell_level[rule]?.[cellId]?.[yearIndex(year)];
  if (v === undefined) throw new Error(`no cell value ${cellId} ${year}`);
  return v;
};

export const cellMagnitude = (m: Magnitude, cellId: string, year: number) => at(hazards.magnitudes[m]?.[cellId], year);

export interface SoilReading {
  values: number[];
  normal: number;
}

/** NASA root-zone soil wetness (0 dry .. 1 saturated) for a crop in the picked years, and its 1991–2020 normal. */
export function soilReading(cropKey: string, years: number[]): SoilReading | null {
  const s = soil.crops[cropKey];
  if (!s || !years.length) return null;
  return { values: years.map((y) => at(s.values, y)), normal: s.normal_1991_2020 };
}
