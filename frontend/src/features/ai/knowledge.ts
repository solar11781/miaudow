import { model } from '../../data';
import { RULES } from '../../domain/hazards';
import { CROPS, PLANS, planProfitMillion } from '../../domain/plans';
import type { Bilingual, EvidenceKind, SourceId } from '../../domain/provenance';

export interface Passage {
  id: string;
  title: Bilingual;
  text: Bilingual;
  /** Extra search words (any language, normalised at index time). */
  keys: string;
  sources: SourceId[];
  kind: EvidenceKind;
}

const n1 = (v: number, lang: 'vi' | 'en') => v.toFixed(1).replace('.', lang === 'vi' ? ',' : '.');

// Hand-written passages: each states what a source says, with its limits. No new findings.
const STATIC: Passage[] = [
  {
    id: 'nasa-power', kind: 'data', sources: ['nasa-power'], keys: 'nasa power du lieu thoi tiet reanalysis merra ve tinh luoi 50 km',
    title: { vi: 'Dữ liệu NASA POWER là gì?', en: 'What is the NASA POWER data?' },
    text: {
      vi: 'NASA POWER cho thời tiết theo ngày trên lưới ô khoảng 50 km. Đây là dữ liệu tái phân tích: một mô hình vật lý khớp với vệ tinh và trạm đo. Miaudow dùng 5 ô có đất trồng ở Nghệ An, 1990–2024. Ô lưới làm mượt cực trị và không đo ruộng nhà bạn.',
      en: 'NASA POWER gives daily weather on a grid of about 50 km. It is reanalysis: a physics model fitted to satellites and stations. Miaudow uses the 5 cells with farmland in Nghệ An, 1990–2024. Grid cells smooth extremes and do not measure your field.',
    },
  },
  {
    id: 'modis', kind: 'data', sources: ['modis'], keys: 'modis trong so dat trong farmland weight',
    title: { vi: 'Vì sao tính theo “phần đất trồng”?', en: 'Why “share of farmland”?' },
    text: {
      vi: 'Mỗi ô NASA được cân theo phần đất trồng trong ô (bản đồ NASA MODIS). Con số trên thẻ là tổng trọng số của các ô đạt ngưỡng, nên ô có nhiều ruộng nặng ký hơn ô núi rừng.',
      en: 'Each NASA cell is weighted by its farmland share (NASA MODIS map). The number on a card is the sum of weights of the cells meeting the rule, so cells with more fields count more than forest cells.',
    },
  },
  {
    id: 'qd18', kind: 'standard', sources: ['qd18'], keys: 'quyet dinh 18 2021 cap do rui ro nguong luat thien tai',
    title: { vi: 'Ngưỡng rủi ro lấy từ đâu?', en: 'Where do the risk thresholds come from?' },
    text: {
      vi: 'Từ Quyết định 18/2021/QĐ-TTg về cấp độ rủi ro thiên tai: mưa lớn Điều 44, nắng nóng Điều 47, hạn (phần mưa) Điều 48, rét hại Điều 53. Miaudow tính từ cấp độ 1 trở lên. Đây là cách đọc máy móc các bảng, không phải cảnh báo chính thức.',
      en: 'From Decision 18/2021/QĐ-TTg on disaster risk levels: heavy rain Art. 44, heat Art. 47, drought rain part Art. 48, damaging cold Art. 53. Miaudow counts level 1 or higher. It is a mechanical reading of the tables, not an official warning.',
    },
  },
  {
    id: 'p02-design', kind: 'study', sources: ['p02'], keys: 'p02 thu nghiem luu son do luong o 1000 m2 khong lap lai co cau',
    title: { vi: 'Thử nghiệm P-02 được làm thế nào?', en: 'How was the P-02 trial done?' },
    text: {
      vi: 'Thử nghiệm ở xã Lưu Sơn, Đô Lương, từ tháng 6/2020 đến tháng 6/2021, trên đất lúa kém hiệu quả, thường xuyên khô hạn. Mỗi cây một ô 1.000 m², không lặp lại. Bài không nói cả chuỗi ba vụ có trồng liền trên một ruộng hay không.',
      en: 'The trial ran in Lưu Sơn, Đô Lương, from June 2020 to June 2021 on inefficient, drought-prone rice land. One 1,000 m² plot per crop, not replicated. The paper does not say whether one field carried each whole sequence.',
    },
  },
  {
    id: 'p03-summer', kind: 'study', sources: ['p03'], keys: 'p03 lua he thu loi nhuan 1 16 gan nhu khong co bo hoang',
    title: { vi: 'Lúa hè thu trên ruộng thiếu nước lãi bao nhiêu?', en: 'What does summer rice earn on water-short land?' },
    text: {
      vi: 'Nghiên cứu P-03 ở Lưu Sơn ghi lúa hè thu năm 2020 lãi 1,16 triệu đồng/ha, “gần như không có lợi nhuận”. Cách tính lãi khác P-02. P-03 mô tả cách làm hiện nay là “Lúa – lúa – bỏ hoang”.',
      en: 'Study P-03 in Lưu Sơn records 2020 summer rice profit of 1.16 million VND/ha, “almost no profit”. Its profit definition differs from P-02. P-03 describes current practice as “rice – rice – fallow”.',
    },
  },
  {
    id: 'no-forecast', kind: 'derived', sources: ['nasa-power', 'nso'], keys: 'du bao mua toi nam sau tuong lai forecast next season',
    title: { vi: 'Ứng dụng có dự báo mùa tới không?', en: 'Does the app forecast the next season?' },
    text: {
      vi: 'Không. Miaudow chỉ cho xem những năm đã qua (1995–2024) và các cách trồng đã được thử. Năm đã qua không phải dự báo; thời tiết năm tới có thể khác.',
      en: 'No. Miaudow shows past years (1995–2024) and plans that were tested. A past year is not a forecast; next year’s weather may differ.',
    },
  },
  {
    id: 'water-units', kind: 'standard', sources: ['tcvn8641', 'fao-tm3'], keys: 'nuoc tuoi m3 ha mm tcvn fao nhu cau nuoc lua lac ngo',
    title: { vi: 'Lúa và các cây khác cần bao nhiêu nước?', en: 'How much water do rice and other crops need?' },
    text: {
      vi: 'Theo TCVN 8641:2011, lúa xuân vùng Trung bộ cần tưới dưỡng 6.500–7.500 m³/ha; ngô 2.000–2.500; lạc và đậu tương khoảng 2.000; khoai lang 1.200–1.400 m³/ha. FAO ước tính thô nhu cầu nước cả vụ: lúa 450–700 mm, lạc 500–700, ngô 500–800. 1 m³/ha bằng 0,1 mm. Tiêu chuẩn không nói Nghệ An thuộc vùng nào.',
      en: 'Under TCVN 8641:2011, central-region spring rice needs 6,500–7,500 m³/ha of maintenance irrigation; maize 2,000–2,500; peanut and soybean about 2,000; sweet potato 1,200–1,400 m³/ha. FAO’s rough seasonal water need: rice 450–700 mm, peanut 500–700, maize 500–800. 1 m³/ha is 0.1 mm. The standard does not say which region Nghệ An is in.',
    },
  },
  {
    id: 'soil-wetness', kind: 'derived', sources: ['nasa-power'], keys: 'do am dat gwetroot merra 2 soil wetness',
    title: { vi: 'Độ ẩm đất NASA nghĩa là gì?', en: 'What does NASA soil wetness mean?' },
    text: {
      vi: 'Là giá trị mô hình MERRA-2 cho lớp đất quanh rễ, từ 0 (khô) đến 1 (bão hòa), trung bình trong thời gian cây trên ruộng, so với 1991–2020. Không phải số đo tại ruộng và không có ngưỡng tốt xấu.',
      en: 'A MERRA-2 model value for the root zone, from 0 (dry) to 1 (saturated), averaged over the crop’s field time and compared with 1991–2020. Not a field measurement, with no good or bad threshold.',
    },
  },
  {
    id: 'officer', kind: 'derived', sources: ['p02'], keys: 'can bo khuyen nong hoi ai giup vay von thu mua gia ban',
    title: { vi: 'Nên hỏi cán bộ khuyến nông điều gì?', en: 'What to ask the extension officer?' },
    text: {
      vi: 'Ruộng nhà mình có giống ruộng thử nghiệm ở Lưu Sơn không; ở xã ai thu mua và giá bao nhiêu; cần bao nhiêu vốn và có được vay không. Giá trong thử nghiệm là giá lúc thu hoạch năm 2020–21.',
      en: 'Whether your field is like the Lưu Sơn trial field; who buys in your commune and at what price; how much capital is needed and whether you can borrow. Trial prices are 2020–21 harvest prices.',
    },
  },
];

function planPassages(): Passage[] {
  return PLANS.filter((p) => p.crops.length).map((p) => {
    const total = planProfitMillion(p) ?? 0;
    const seq = (lang: 'vi' | 'en') => p.crops.map((c) => CROPS[c.crop].name[lang]).join(' → ');
    const parts = (lang: 'vi' | 'en') => p.crops.map((c) => `${CROPS[c.crop].name[lang]} ${n1(c.profit / 1000, lang)}`).join(', ');
    return {
      id: `plan-${p.id}`, kind: 'study', sources: ['p02'],
      keys: `${p.id} ${p.crops.map((c) => `${CROPS[c.crop].name.vi} ${CROPS[c.crop].name.en} ${c.variety}`).join(' ')} lai co cau`,
      title: { vi: `${p.current ? 'Cách làm hiện nay' : `Cơ cấu ${p.id.toUpperCase()}`}: ${seq('vi')}`, en: `${p.current ? 'Current practice' : `Plan ${p.id.toUpperCase()}`}: ${seq('en')}` },
      text: {
        vi: `Trong thử nghiệm P-02 (2020–21), lãi đã trừ công của từng vụ (triệu đồng/ha): ${parts('vi')}; cộng lại ${n1(total, 'vi')} triệu đồng/ha (phép cộng của Miaudow). Một ô thử, một năm; giá bán năm nay có thể khác.`,
        en: `In the P-02 trial (2020–21), profit net of labour per season (million VND/ha): ${parts('en')}; ${n1(total, 'en')} in total (Miaudow’s sum). One plot, one year; this year’s prices may differ.`,
      },
    };
  });
}

function rulePassages(): Passage[] {
  return Object.values(RULES).map((r) => ({
    id: `rule-${r.code}`, kind: 'standard' as const, sources: ['qd18', 'nasa-power'] as SourceId[],
    keys: `${r.name.vi} ${r.name.en} ${r.article} nguong`,
    title: { vi: `Luật “${r.name.vi}” tính thế nào?`, en: `How is the “${r.name.en}” rule computed?` },
    text: { vi: `${r.article}: “${r.quote}”. ${r.computed.vi}`, en: `${r.article}: “${r.quote}”. ${r.computed.en}` },
  }));
}

function modelPassages(): Passage[] {
  const g = (season: string) => model.gates.find((x) => x.gate === 'G2' && x.season === season);
  return [
    {
      id: 'model-spring', kind: 'model', sources: ['e012'], keys: 'mo hinh du doan lua xuan spring skill bnw khong thang',
      title: { vi: 'Mô hình dự đoán lúa xuân có tốt không?', en: 'Is the spring rice model any good?' },
      text: {
        vi: `Chưa đủ tốt để hiện. Trên các năm kiểm tra 2016–2024, mô hình có thời tiết NASA không vượt rõ ràng cùng mô hình bỏ thời tiết: ${g('spring')?.detail.vi ?? ''} Vì vậy Miaudow không hiện dự đoán lúa xuân, chỉ hiện số liệu thật.`,
        en: `Not good enough to show. On the 2016–2024 test years the model with NASA weather did not clearly beat the same model without weather: ${g('spring')?.detail.en ?? ''} So Miaudow shows no spring prediction, only real values.`,
      },
    },
    {
      id: 'model-winter', kind: 'model', sources: ['e012'], keys: 'mo hinh du doan lua mua winter skill thang',
      title: { vi: 'Mô hình dự đoán lúa mùa thì sao?', en: 'What about the winter rice model?' },
      text: {
        vi: `Lúa mùa qua bài kiểm tra với mức hơn nhỏ: ${g('winter')?.detail.vi ?? ''} Dự đoán ngoài mẫu 2016–2024 được hiện cạnh số liệu thật, kèm khoảng 80%.`,
        en: `Winter rice passed by a small margin: ${g('winter')?.detail.en ?? ''} Out-of-sample predictions for 2016–2024 are shown next to the real values, with an 80% range.`,
      },
    },
  ];
}

export const PASSAGES: Passage[] = [...STATIC, ...planPassages(), ...rulePassages(), ...modelPassages()];
