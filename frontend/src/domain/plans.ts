import type { Bilingual } from './provenance';

/** Plain name of a plan: "current practice" or "trial way of farming n", in the reader's language. */
export function planLabel(
  p: { id: string; current?: boolean },
  text: { current: string; trialShort: (n: string) => string },
): string {
  return p.current ? text.current : text.trialShort(p.id.replace(/\D/g, ''));
}

interface StudyNames {
  usual: string;
  usual_p03: string;
}

/** The study a current-practice plan comes from (F-B2): the control of the trial the four trial plans come from
 * (`usual`, P-02) or of another study (`usual_p03`, P-03); nothing for a trial plan. */
export const studyOf = (id: string, names: StudyNames) =>
  id === 'usual' || id === 'usual_p03' ? names[id] : undefined;

/** The plan's label with, for a current-practice plan, its study. */
export function planName(
  p: { id: string; is_usual: boolean },
  text: { current: string; trialShort: (n: string) => string; currentOf: StudyNames },
): string {
  return [planLabel({ id: p.id, current: p.is_usual }, text), studyOf(p.id, text.currentOf)]
    .filter(Boolean)
    .join(' · ');
}

/** The two short lines of a plan's jump-strip chip (F-A7). */
export function chipLines(
  id: string,
  chip: { usual: string[]; usual_p03: string[]; trial: (n: string) => string[] },
): string[] {
  if (id === 'usual' || id === 'usual_p03') return chip[id];
  return chip.trial(id.replace(/\D/g, ''));
}

// Crop facts as published. Money in thousand VND per hectare (P-02 Table 13, net of labour; costs from Tables 4, 8, 12).
export type CropFamily = 'rice' | 'legume' | 'maize' | 'root' | 'other';
export type Season = 'spring' | 'summer' | 'autumn';

export interface CropInfo {
  name: Bilingual;
  family: CropFamily;
  legume: boolean;
  /** TCVN 8641:2011 seasonal irrigation, m³/ha, where the standard lists the crop: every row of rules/crops.yaml for the
   * trial's season, each with its scope, since the standard does not place Nghệ An in a region (D-68). */
  tcvn?: readonly TcvnRow[];
  /** FAO TM3 Table 14 seasonal water need, mm, where FAO lists the crop. */
  fao?: string;
}

export interface TcvnRow {
  value: Bilingual;
  scope?: Bilingual;
}

const tcvn = (vi: string, en: string): TcvnRow[] => [{ value: { vi, en } }];

export const CROPS = {
  rice: {
    name: { vi: 'Lúa', en: 'Rice' },
    family: 'rice',
    legume: false,
    tcvn: [
      {
        value: { vi: '6.500–7.500', en: '6,500–7,500' },
        scope: { vi: 'Trung bộ, lúa cấy, vụ xuân', en: 'Trung Bo, transplanted rice, spring season' },
      },
      {
        value: { vi: '6.500–7.500', en: '6,500–7,500' },
        scope: { vi: 'Trung bộ, lúa gieo thẳng, vụ xuân', en: 'Trung Bo, direct-seeded rice, spring season' },
      },
      {
        value: { vi: '6.000–7.000', en: '6,000–7,000' },
        scope: { vi: 'Bắc bộ, vụ xuân', en: 'Bac Bo, spring season' },
      },
    ],
    fao: '450–700',
  },
  blackbean: { name: { vi: 'Đậu đen xanh lòng', en: 'Black bean' }, family: 'legume', legume: true },
  sweetpotato: {
    name: { vi: 'Khoai lang', en: 'Sweet potato' },
    family: 'root',
    legume: false,
    tcvn: tcvn('1.200–1.400', '1,200–1,400'),
  },
  peanut: {
    name: { vi: 'Lạc', en: 'Peanut' },
    family: 'legume',
    legume: true,
    tcvn: tcvn('khoảng 2.000', 'about 2,000'),
    fao: '500–700',
  },
  mung: { name: { vi: 'Đậu xanh', en: 'Mung bean' }, family: 'legume', legume: true },
  maize: {
    name: { vi: 'Ngô thương phẩm', en: 'Grain maize' },
    family: 'maize',
    legume: false,
    tcvn: tcvn('2.000–2.500', '2,000–2,500'),
    fao: '500–800',
  },
  chili: { name: { vi: 'Ớt chỉ thiên', en: 'Chili' }, family: 'other', legume: false },
  soy: {
    name: { vi: 'Đậu tương', en: 'Soybean' },
    family: 'legume',
    legume: true,
    tcvn: tcvn('khoảng 2.000', 'about 2,000'),
    fao: '450–700',
  },
  biomaize: { name: { vi: 'Ngô sinh khối', en: 'Biomass maize' }, family: 'maize', legume: false },
  sesame: { name: { vi: 'Vừng đen', en: 'Black sesame' }, family: 'other', legume: false },
  pumpkin: { name: { vi: 'Bí đỏ', en: 'Pumpkin' }, family: 'root', legume: false },
} as const satisfies Record<string, CropInfo>;

export type CropId = keyof typeof CROPS;

export interface PlanCrop {
  /** Key into the generated hazard and soil data (pipeline/build_data.py). */
  key: string;
  crop: CropId;
  /** As the paper names it; empty when the paper names none. */
  variety: string;
  season: Season;
  /** MM-DD as reported (sowing, first reported harvest). */
  sow: string;
  harvest: string;
  harvestNote?: string;
  days: string;
  /** Net profit, thousand VND/ha. */
  profit: number;
  /** Total cost, thousand VND/ha. */
  cost: number;
  /** Sale price, VND/kg, market price at harvest. */
  price: number;
}

export type PlanId = 'cc5' | 'p03' | 'cc1' | 'cc2' | 'cc3' | 'cc4';

export interface Plan {
  id: PlanId;
  current: boolean;
  source: 'p02' | 'p03';
  crops: PlanCrop[];
  /** P-03 has no dates: the plan is described by text only. */
  textOnly?: { sequence: Bilingual; profitNote: Bilingual };
}

export const PLANS: Plan[] = [
  {
    id: 'cc5',
    current: true,
    source: 'p02',
    crops: [
      {
        key: 'cc5_rice',
        crop: 'rice',
        variety: 'Khang dân',
        season: 'spring',
        sow: '01-17',
        harvest: '05-17',
        days: '121',
        profit: 5149,
        cost: 32426,
        price: 7500,
      },
      {
        key: 'cc5_blackbean',
        crop: 'blackbean',
        variety: 'VT1',
        season: 'summer',
        sow: '06-06',
        harvest: '08-25',
        days: '80–85',
        profit: 16200,
        cost: 25000,
        price: 40000,
      },
      {
        key: 'cc5_sweetpotato',
        crop: 'sweetpotato',
        variety: 'Chiêm Dâu',
        season: 'autumn',
        sow: '08-15',
        harvest: '12-10',
        days: '115',
        profit: 9450,
        cost: 40800,
        price: 5000,
      },
    ],
  },
  {
    id: 'p03',
    current: true,
    source: 'p03',
    crops: [],
    textOnly: {
      sequence: { vi: 'Lúa vụ Đông Xuân – lúa vụ Hè Thu – bỏ hoang', en: 'Spring rice – summer-autumn rice – fallow' },
      profitNote: {
        vi: 'Lúa vụ Đông Xuân 2021: 5,36 triệu đồng/ha; lúa vụ Hè Thu 2020: 1,16 triệu đồng/ha, “gần như không có lợi nhuận” (tính lãi theo cách khác bài báo thứ nhất của Trịnh Đức Toàn và cs., 2023)',
        en: 'Spring rice 2021: 5.36 million VND/ha; summer-autumn rice 2020: 1.16 million VND/ha, “almost no profit” (profit defined differently from the first paper of Trịnh Đức Toàn et al., 2023)',
      },
    },
  },
  {
    id: 'cc1',
    current: false,
    source: 'p02',
    crops: [
      {
        key: 'cc1_peanut',
        crop: 'peanut',
        variety: 'L20',
        season: 'spring',
        sow: '01-18',
        harvest: '05-12',
        days: '115',
        profit: 25980,
        cost: 83500,
        price: 28000,
      },
      {
        key: 'cc1_mung',
        crop: 'mung',
        variety: 'D22',
        season: 'summer',
        sow: '06-10',
        harvest: '08-30',
        harvestNote: '30/8 – 3/9',
        days: '80–83',
        profit: 16200,
        cost: 25000,
        price: 40000,
      },
      {
        key: 'cc1_maize',
        crop: 'maize',
        variety: 'VN5885',
        season: 'autumn',
        sow: '09-01',
        harvest: '12-22',
        days: '112',
        profit: 11200,
        cost: 29900,
        price: 6000,
      },
    ],
  },
  {
    id: 'cc2',
    current: false,
    source: 'p02',
    crops: [
      {
        key: 'cc2_chili',
        crop: 'chili',
        variety: 'F1',
        season: 'spring',
        sow: '01-17',
        harvest: '06-25',
        days: '157',
        profit: 21100,
        cost: 113100,
        price: 11000,
      },
      {
        key: 'cc2_soy',
        crop: 'soy',
        variety: 'ĐT51',
        season: 'summer',
        sow: '06-10',
        harvest: '09-09',
        harvestNote: '9 – 12/9',
        days: '90–93',
        profit: 16700,
        cost: 26500,
        price: 40000,
      },
      {
        key: 'cc2_biomaize',
        crop: 'biomaize',
        variety: 'NK7328',
        season: 'autumn',
        sow: '09-10',
        harvest: '11-26',
        days: '76',
        profit: 15865,
        cost: 27400,
        price: 850,
      },
    ],
  },
  {
    id: 'cc3',
    current: false,
    source: 'p02',
    crops: [
      {
        key: 'cc3_maize',
        crop: 'maize',
        variety: 'VN5885',
        season: 'spring',
        sow: '01-17',
        harvest: '05-04',
        days: '110',
        profit: 12420,
        cost: 29100,
        price: 6000,
      },
      {
        key: 'cc3_sesame',
        crop: 'sesame',
        variety: '',
        season: 'summer',
        sow: '06-10',
        harvest: '09-04',
        days: '84',
        profit: 12500,
        cost: 23500,
        price: 50000,
      },
      {
        key: 'cc3_pumpkin',
        crop: 'pumpkin',
        variety: 'F1 Flato 757 - Én vàng',
        season: 'autumn',
        sow: '09-05',
        harvest: '11-21',
        days: '70–77',
        profit: 30440,
        cost: 48200,
        price: 8000,
      },
    ],
  },
  {
    id: 'cc4',
    current: false,
    source: 'p02',
    crops: [
      {
        key: 'cc4_biomaize1',
        crop: 'biomaize',
        variety: 'NK7328',
        season: 'spring',
        sow: '01-17',
        harvest: '04-05',
        days: '77',
        profit: 18925,
        cost: 27400,
        price: 850,
      },
      {
        key: 'cc4_biomaize2',
        crop: 'biomaize',
        variety: 'NK7328',
        season: 'summer',
        sow: '06-10',
        harvest: '08-20',
        days: '70',
        profit: 19450,
        cost: 27300,
        price: 850,
      },
      {
        key: 'cc4_sweetpotato',
        crop: 'sweetpotato',
        variety: 'KL20-209',
        season: 'autumn',
        sow: '09-05',
        harvest: '12-02',
        days: '115',
        profit: 20390,
        cost: 63200,
        price: 6500,
      },
    ],
  },
];

/** Sum of the per-crop profits, our arithmetic on Table 13, in million VND/ha. */
export const planProfitMillion = (plan: Plan): number | null =>
  plan.crops.length ? Math.round(plan.crops.reduce((s, c) => s + c.profit, 0)) / 1000 : null;

export const planHasLegume = (plan: Plan) => plan.crops.some((c) => CROPS[c.crop].legume);
