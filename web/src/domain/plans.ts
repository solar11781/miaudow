import type { Bilingual } from './provenance';

// Crop facts as published. Money in thousand VND per hectare (P-02 Table 13, net of labour; costs from Tables 4, 8, 12).
export type CropFamily = 'rice' | 'legume' | 'maize' | 'root' | 'other';
export type Season = 'spring' | 'summer' | 'autumn';

export interface CropInfo {
  name: Bilingual;
  family: CropFamily;
  legume: boolean;
  /** TCVN 8641:2011 seasonal irrigation, m³/ha, where the standard lists the crop. */
  tcvn?: Bilingual;
  /** FAO TM3 Table 14 seasonal water need, mm, where FAO lists the crop. */
  fao?: string;
}

export const CROPS = {
  rice: { name: { vi: 'Lúa', en: 'Rice' }, family: 'rice', legume: false,
    tcvn: { vi: '6.500–7.500 (vụ xuân, Trung bộ, chỉ tưới dưỡng)', en: '6,500–7,500 (spring, central region, maintenance only)' }, fao: '450–700' },
  blackbean: { name: { vi: 'Đậu đen', en: 'Black bean' }, family: 'legume', legume: true },
  sweetpotato: { name: { vi: 'Khoai lang', en: 'Sweet potato' }, family: 'root', legume: false, tcvn: { vi: '1.200–1.400', en: '1,200–1,400' } },
  peanut: { name: { vi: 'Lạc', en: 'Peanut' }, family: 'legume', legume: true, tcvn: { vi: 'khoảng 2.000', en: 'about 2,000' }, fao: '500–700' },
  mung: { name: { vi: 'Đậu xanh', en: 'Mung bean' }, family: 'legume', legume: true },
  maize: { name: { vi: 'Ngô hạt', en: 'Grain maize' }, family: 'maize', legume: false, tcvn: { vi: '2.000–2.500', en: '2,000–2,500' }, fao: '500–800' },
  chili: { name: { vi: 'Ớt', en: 'Chili' }, family: 'other', legume: false },
  soy: { name: { vi: 'Đậu tương', en: 'Soybean' }, family: 'legume', legume: true, tcvn: { vi: 'khoảng 2.000', en: 'about 2,000' }, fao: '450–700' },
  biomaize: { name: { vi: 'Ngô sinh khối', en: 'Biomass maize' }, family: 'maize', legume: false },
  sesame: { name: { vi: 'Vừng đen', en: 'Black sesame' }, family: 'other', legume: false },
  pumpkin: { name: { vi: 'Bí đỏ', en: 'Pumpkin' }, family: 'root', legume: false },
} as const satisfies Record<string, CropInfo>;

export type CropId = keyof typeof CROPS;

export interface PlanCrop {
  /** Key into the generated hazard and soil data (pipeline/build_data.py). */
  key: string;
  crop: CropId;
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
  checks: Bilingual[];
}

export const PLANS: Plan[] = [
  {
    id: 'cc5', current: true, source: 'p02',
    crops: [
      { key: 'cc5_rice', crop: 'rice', variety: 'Khang dân', season: 'spring', sow: '01-17', harvest: '05-17', days: '121', profit: 5149, cost: 32426, price: 7500 },
      { key: 'cc5_blackbean', crop: 'blackbean', variety: 'VT1', season: 'summer', sow: '06-06', harvest: '08-25', days: '80–85', profit: 16200, cost: 25000, price: 40000 },
      { key: 'cc5_sweetpotato', crop: 'sweetpotato', variety: 'Chiêm Dâu', season: 'autumn', sow: '08-15', harvest: '12-10', days: '115', profit: 9450, cost: 40800, price: 5000 },
    ],
    checks: [
      { vi: 'Lúa xuân chỉ lãi khoảng 5 triệu đồng/ha trong thử nghiệm.', en: 'Spring rice made about 5 million VND/ha in the trial.' },
      { vi: 'Khoai lang được gieo trước khi đậu đen thu hoạch (ngày báo cáo chồng nhau).', en: 'Sweet potato was sown before the black bean harvest (reported dates overlap).' },
    ],
  },
  {
    id: 'p03', current: true, source: 'p03', crops: [],
    textOnly: {
      sequence: { vi: 'Lúa xuân – lúa hè thu – bỏ hoang', en: 'Spring rice – summer rice – fallow' },
      profitNote: { vi: 'Lúa hè thu lãi 1,16 triệu đồng/ha, “gần như không có lợi nhuận” (tính lãi theo cách khác P-02)', en: 'Summer rice made 1.16 million VND/ha, “almost no profit” (profit defined differently from P-02)' },
    },
    checks: [
      { vi: 'Ruộng bỏ trống sau vụ hè thu.', en: 'The field lies bare after the summer crop.' },
      { vi: 'Bài không ghi ngày gieo, nên không có lịch và không tính được thời tiết theo cây.', en: 'No sowing dates are given, so there is no calendar and no weather per crop.' },
    ],
  },
  {
    id: 'cc1', current: false, source: 'p02',
    crops: [
      { key: 'cc1_peanut', crop: 'peanut', variety: 'L20', season: 'spring', sow: '01-18', harvest: '05-12', days: '115', profit: 25980, cost: 83500, price: 28000 },
      { key: 'cc1_mung', crop: 'mung', variety: 'D22', season: 'summer', sow: '06-10', harvest: '08-30', harvestNote: '30/8 – 3/9', days: '80–83', profit: 16200, cost: 25000, price: 40000 },
      { key: 'cc1_maize', crop: 'maize', variety: 'VN5885', season: 'autumn', sow: '09-01', harvest: '12-22', days: '112', profit: 11200, cost: 29900, price: 6000 },
    ],
    checks: [
      { vi: 'Lạc cần vốn lớn: chi phí khoảng 83,5 triệu đồng/ha, gấp hơn 2 lần lúa.', en: 'Peanut needs capital: about 83.5 million VND/ha, more than twice the rice cost.' },
      { vi: 'Ngô được gieo 1/9, trước khi đậu xanh thu hoạch xong (30/8 – 3/9).', en: 'Maize was sown on 1 Sep, before the mung bean harvest ended (30 Aug – 3 Sep).' },
    ],
  },
  {
    id: 'cc2', current: false, source: 'p02',
    crops: [
      { key: 'cc2_chili', crop: 'chili', variety: 'Chỉ thiên F1', season: 'spring', sow: '01-17', harvest: '06-25', days: '157', profit: 21100, cost: 113100, price: 11000 },
      { key: 'cc2_soy', crop: 'soy', variety: 'ĐT51', season: 'summer', sow: '06-10', harvest: '09-09', harvestNote: '9 – 12/9', days: '90–93', profit: 16700, cost: 26500, price: 40000 },
      { key: 'cc2_biomaize', crop: 'biomaize', variety: 'NK7328', season: 'autumn', sow: '09-10', harvest: '11-26', days: '76', profit: 15865, cost: 27400, price: 850 },
    ],
    checks: [
      { vi: 'Ớt có chi phí cao nhất: khoảng 113 triệu đồng/ha.', en: 'Chili has the highest cost: about 113 million VND/ha.' },
      { vi: 'Ngô sinh khối cần người mua làm thức ăn gia súc; nên có hợp đồng trước.', en: 'Biomass maize needs a cattle-feed buyer; a contract first is advisable.' },
    ],
  },
  {
    id: 'cc3', current: false, source: 'p02',
    crops: [
      { key: 'cc3_maize', crop: 'maize', variety: 'VN5885', season: 'spring', sow: '01-17', harvest: '05-04', days: '110', profit: 12420, cost: 29100, price: 6000 },
      { key: 'cc3_sesame', crop: 'sesame', variety: 'Vừng đen', season: 'summer', sow: '06-10', harvest: '09-04', days: '84', profit: 12500, cost: 23500, price: 50000 },
      { key: 'cc3_pumpkin', crop: 'pumpkin', variety: 'F1 Flato 757', season: 'autumn', sow: '09-05', harvest: '11-21', days: '70–77', profit: 30440, cost: 48200, price: 8000 },
    ],
    checks: [
      { vi: 'Nghiên cứu P-03 ghi vừng khó bán ở Lưu Sơn.', en: 'The P-03 study reports sesame was hard to sell in Lưu Sơn.' },
      { vi: 'Phần lớn tiền lãi đến từ bí đỏ; hỏi trước nơi thu mua.', en: 'Most of the profit comes from pumpkin; find a buyer first.' },
    ],
  },
  {
    id: 'cc4', current: false, source: 'p02',
    crops: [
      { key: 'cc4_biomaize1', crop: 'biomaize', variety: 'NK7328', season: 'spring', sow: '01-17', harvest: '04-05', days: '77', profit: 18925, cost: 27400, price: 850 },
      { key: 'cc4_biomaize2', crop: 'biomaize', variety: 'NK7328', season: 'summer', sow: '06-10', harvest: '08-20', days: '70', profit: 19450, cost: 27300, price: 850 },
      { key: 'cc4_sweetpotato', crop: 'sweetpotato', variety: 'KL20-209', season: 'autumn', sow: '09-05', harvest: '12-02', days: '115', profit: 20390, cost: 63200, price: 6500 },
    ],
    checks: [
      { vi: 'Hai vụ ngô liền nhau: theo dõi sâu bệnh.', en: 'Two maize crops in a row: watch for pests.' },
      { vi: 'Tỉnh yêu cầu hợp đồng thu mua cho ngô sinh khối.', en: 'The province requires purchase contracts for biomass maize.' },
    ],
  },
];

export const planById = (id: PlanId) => PLANS.find((p) => p.id === id);

/** Sum of the per-crop profits, our arithmetic on Table 13, in million VND/ha. */
export const planProfitMillion = (plan: Plan): number | null =>
  plan.crops.length ? Math.round(plan.crops.reduce((s, c) => s + c.profit, 0)) / 1000 : null;

export const planHasLegume = (plan: Plan) => plan.crops.some((c) => CROPS[c.crop].legume);

export const planCropCount = (plan: Plan) => new Set(plan.crops.map((c) => c.crop)).size;
