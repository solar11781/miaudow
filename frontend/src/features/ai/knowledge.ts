import { model } from '../../data';
import { lowerFirst, upperFirst } from '../../domain/format';
import { RULES } from '../../domain/hazards';
import { CROPS, PLANS, planLabel, planProfitMillion } from '../../domain/plans';
import type { Bilingual, EvidenceKind, SourceId } from '../../domain/provenance';
import { modelVerdict, type ModelVerdict } from '../../domain/rice';
import { en } from '../../i18n/en';
import { vi } from '../../i18n/vi';

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
    id: 'nasa-power',
    kind: 'data',
    sources: ['nasa-power'],
    keys: 'nasa power du lieu thoi tiet reanalysis merra ve tinh luoi 50 km',
    title: { vi: 'Dữ liệu NASA POWER là gì?', en: 'What is the NASA POWER data?' },
    text: {
      vi: 'NASA POWER cho thời tiết theo ngày trên lưới ô, mỗi ô khoảng 55 × 66 km. Đây là dữ liệu tái phân tích: một mô hình vật lý khớp với vệ tinh và trạm đo. Miaudow dùng 5 ô có đất trồng ở Nghệ An, 1990–2024. Ô lưới làm mượt cực trị và không đo ruộng nhà bạn.',
      en: 'NASA POWER gives daily weather on a grid of cells about 55 × 66 km. It is reanalysis: a physics model fitted to satellites and stations. Miaudow uses the 5 cells with farmland in Nghệ An, 1990–2024. Grid cells smooth extremes and do not measure your field.',
    },
  },
  {
    id: 'modis',
    kind: 'data',
    sources: ['modis'],
    keys: 'modis trong so dat trong farmland weight',
    title: { vi: 'Vì sao tính theo “phần đất trồng”?', en: 'Why “share of farmland”?' },
    text: {
      vi: 'Mỗi ô NASA được cân theo phần đất trồng trong ô (bản đồ NASA MODIS). Con số trên thẻ là tổng trọng số của các ô đạt ngưỡng, nên ô có nhiều ruộng nặng ký hơn ô núi rừng.',
      en: 'Each NASA cell is weighted by its farmland share (NASA MODIS map). The number on a card is the sum of weights of the cells meeting the threshold, so cells with more fields count more than forest cells.',
    },
  },
  {
    id: 'qd18',
    kind: 'standard',
    sources: ['qd18'],
    keys: 'quyet dinh 18 2021 cap do rui ro nguong luat thien tai',
    title: { vi: 'Ngưỡng rủi ro lấy từ đâu?', en: 'Where do the risk thresholds come from?' },
    text: {
      vi: 'Từ Quyết định 18/2021/QĐ-TTg về cấp độ rủi ro thiên tai: mưa lớn Điều 44, nắng nóng Điều 47, hạn hán (phần lượng mưa) Điều 48, rét hại Điều 53. Miaudow tính từ cấp độ 1 trở lên. Đây là cách đọc máy móc các bảng, không phải cảnh báo chính thức.',
      en: 'From Decision 18/2021/QĐ-TTg on disaster risk levels: heavy rain Art. 44, heat Art. 47, drought (rain part) Art. 48, damaging cold Art. 53. Miaudow counts level 1 or higher. It is a mechanical reading of the tables, not an official warning.',
    },
  },
  {
    id: 'p02-design',
    kind: 'study',
    sources: ['p02'],
    keys: 'p02 thu nghiem luu son do luong o 1000 m2 khong lap lai co cau',
    title: { vi: 'Thử nghiệm ở Lưu Sơn được làm thế nào?', en: 'How was the Lưu Sơn trial done?' },
    text: {
      vi: 'Thử nghiệm ở xã Lưu Sơn, Đô Lương, từ tháng 6/2020 đến tháng 6/2021, trên đất lúa kém hiệu quả, thường xuyên khô hạn. Mỗi cây một ô 1.000 m², không lặp lại. Bài không nói cả chuỗi ba vụ có trồng liền trên một ruộng hay không.',
      en: 'The trial ran in Lưu Sơn, Đô Lương, from June 2020 to June 2021 on low-return (inefficient) rice land, often in drought. One 1,000 m² plot per crop, not replicated. The paper does not say whether one field carried each whole sequence.',
    },
  },
  {
    id: 'p03-summer',
    kind: 'study',
    sources: ['p03'],
    keys: 'p03 lua he thu loi nhuan 1 16 gan nhu khong co bo hoang',
    title: {
      vi: 'Lúa vụ Hè Thu trên ruộng thiếu nước lãi bao nhiêu?',
      en: 'What does summer-autumn rice earn on water-short land?',
    },
    text: {
      vi: 'Bài báo thứ hai của Trịnh Đức Toàn và cs. (2023) ghi lúa vụ Hè Thu năm 2020 ở Lưu Sơn lãi 1,16 triệu đồng/ha, “gần như không có lợi nhuận”. Cách tính lãi khác bài báo thứ nhất. Bài này mô tả cách làm hiện nay là “Lúa – lúa – bỏ hoang”.',
      en: 'The second paper of Trịnh Đức Toàn et al. (2023) records 2020 summer-autumn rice profit in Lưu Sơn of 1.16 million VND/ha, “almost no profit”. Its profit definition differs from the first paper. It describes current practice as “rice – rice – fallow”.',
    },
  },
  {
    id: 'no-forecast',
    kind: 'derived',
    sources: ['nasa-power', 'nso'],
    keys: 'du bao mua toi nam sau tuong lai forecast next season',
    title: { vi: 'Ứng dụng có dự báo mùa tới không?', en: 'Does the app forecast the next season?' },
    text: {
      vi: 'Không. Miaudow chỉ cho xem những năm đã qua (1995–2024) và các cách trồng đã được thử. Năm đã qua không phải dự báo; thời tiết năm tới có thể khác.',
      en: 'No. Miaudow shows past years (1995–2024) and plans that were tested. A past year is not a forecast; next year’s weather may differ.',
    },
  },
  // TCVN 8641 and FAO TM3 in separate passages, never combined or converted (D-64, D-68); as rules/copilot.yaml
  {
    id: 'water-tcvn',
    kind: 'standard',
    sources: ['tcvn8641'],
    keys: 'nuoc tuoi m3 ha tcvn nhu cau nuoc lua lac ngo',
    title: {
      vi: 'Theo TCVN 8641:2011, lúa và các cây khác phải tưới bao nhiêu nước?',
      en: 'How much water to apply to rice and other crops, by TCVN 8641:2011?',
    },
    text: {
      vi: 'Theo TCVN 8641:2011, nước phải tưới dưỡng cho lúa vụ xuân là 6.500–7.500 m³/ha (Trung bộ, lúa cấy hoặc lúa gieo thẳng) và 6.000–7.000 m³/ha (Bắc bộ); ngô 2.000–2.500; lạc và đậu tương khoảng 2.000; khoai lang 1.200–1.400 m³/ha. Tiêu chuẩn không nói Nghệ An thuộc vùng nào.',
      en: 'Under TCVN 8641:2011, the water to apply for maintenance irrigation of spring rice is 6,500–7,500 m³/ha (Trung bộ, transplanted or direct-seeded) and 6,000–7,000 m³/ha (Bắc bộ); maize 2,000–2,500; peanut and soybean about 2,000; sweet potato 1,200–1,400 m³/ha. The standard does not say which region Nghệ An is in.',
    },
  },
  {
    id: 'water-fao',
    kind: 'standard',
    sources: ['fao-tm3'],
    keys: 'nuoc mm fao nhu cau nuoc ca vu lua lac ngo',
    title: {
      vi: 'Cả vụ cây cần bao nhiêu nước theo FAO?',
      en: 'How much water does a crop need over a season, by FAO?',
    },
    text: {
      vi: 'FAO ước tính thô nhu cầu nước cả vụ: lúa 450–700 mm, lạc 500–700, ngô 500–800.',
      en: 'FAO’s rough seasonal water need: rice 450–700 mm, peanut 500–700, maize 500–800.',
    },
  },
  {
    id: 'soil-wetness',
    kind: 'derived',
    sources: ['nasa-power'],
    keys: 'do am dat gwetroot merra 2 soil wetness',
    title: { vi: 'Độ ẩm đất NASA nghĩa là gì?', en: 'What does NASA soil wetness mean?' },
    text: {
      vi: 'Là giá trị mô hình MERRA-2 cho lớp đất quanh rễ, từ 0 (khô) đến 1 (bão hòa), trung bình trong thời gian cây trên ruộng, so với 1991–2020. Không phải số đo tại ruộng và không có ngưỡng tốt xấu.',
      en: 'A MERRA-2 model value for the root zone, from 0 (dry) to 1 (saturated), averaged over the crop’s field time and compared with 1991–2020. Not a field measurement, with no good or bad threshold.',
    },
  },
  {
    id: 'officer',
    kind: 'derived',
    sources: ['p02'],
    keys: 'can bo khuyen nong hoi ai giup vay von thu mua gia ban',
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
    const parts = (lang: 'vi' | 'en') =>
      p.crops.map((c) => `${CROPS[c.crop].name[lang]} ${n1(c.profit / 1000, lang)}`).join(', ');
    return {
      id: `plan-${p.id}`,
      kind: 'study',
      sources: ['p02'],
      keys: `${p.id} ${p.crops.map((c) => `${CROPS[c.crop].name.vi} ${CROPS[c.crop].name.en} ${c.variety}`).join(' ')} lai co cau`,
      title: {
        vi: `${planLabel(p, vi.farmer)}: ${seq('vi')}`,
        en: `${planLabel(p, en.farmer)}: ${seq('en')}`,
      },
      text: {
        vi: `Trong thử nghiệm 2020–21 của Trịnh Đức Toàn và cs. (2023), lãi đã trừ công của từng vụ (triệu đồng/ha): ${parts('vi')}; cộng lại ${n1(total, 'vi')} triệu đồng/ha (phép cộng của Miaudow). Một ô thử, một năm; giá bán năm nay có thể khác.`,
        en: `In the 2020–21 trial of Trịnh Đức Toàn et al. (2023), profit net of labour per season (million VND/ha): ${parts('en')}; ${n1(total, 'en')} in total (Miaudow’s sum). One plot, one year; this year’s prices may differ.`,
      },
    };
  });
}

function rulePassages(): Passage[] {
  return Object.values(RULES).map((r) => ({
    id: `rule-${r.code}`,
    kind: 'standard' as const,
    sources: ['qd18', 'nasa-power'] as SourceId[],
    keys: `${r.name.vi} ${r.name.en} ${r.article} nguong`,
    title: { vi: `Luật “${r.name.vi}” tính thế nào?`, en: `How is the “${r.name.en}” rule computed?` },
    text: { vi: `${r.article}: “${r.quote}”. ${r.computed.vi}`, en: `${r.article}: “${r.quote}”. ${r.computed.en}` },
  }));
}

/** Whether a season's test-year estimates are shown, and with their 80% range, as the run decided. */
function shownLine(v: ModelVerdict): Bilingual {
  if (!v.shown) return { vi: vi.science.modelHidden, en: en.science.modelHidden };
  return {
    vi: `Ước tính của mô hình cho năm kiểm tra 2016–2024 được hiện cạnh số liệu thật${v.range ? ', kèm khoảng 80%' : ''}.`,
    en: `The model estimate for each test year 2016–2024 is shown next to the real values${v.range ? ', with an 80% range' : ''}.`,
  };
}

// the answer follows the run's verdict for the season (src/domain/rice.ts modelVerdict), so a re-run cannot leave it
// wrong; D-165: the narrow, fragile wording belongs to the winter result
function modelPassages(): Passage[] {
  const g = (season: string) => model.gates.find((x) => x.gate === 'G2' && x.season === season);
  const question = {
    spring: { vi: 'Mô hình dự đoán lúa vụ Đông Xuân có tốt không?', en: 'Is the spring rice model any good?' },
    winter: { vi: 'Mô hình dự đoán lúa vụ Mùa thì sao?', en: 'What about the winter rice model?' },
  };
  const keys = { spring: 'lua xuan dong xuan spring', winter: 'lua mua winter' };
  return (['spring', 'winter'] as const).map((season) => {
    const v = modelVerdict(season);
    const name = { vi: lowerFirst(vi.science.seasons[season]), en: lowerFirst(en.science.seasons[season]) };
    const detail = { vi: g(season)?.detail.vi ?? '', en: g(season)?.detail.en ?? '' };
    const fragile =
      season === 'winter' ? { vi: ` ${vi.common.winterFragile}.`, en: ` ${en.common.winterFragile}.` } : null;
    const shown = shownLine(v);
    return {
      id: `model-${season}`,
      kind: 'model',
      sources: ['e012'],
      keys: `mo hinh du doan ${keys[season]} skill bnw ${v.weatherHelps ? 'thang' : 'khong thang'}`,
      title: question[season],
      text: v.weatherHelps
        ? {
            vi: `${upperFirst(name.vi)} qua bài kiểm tra, nhưng chỉ hơn một chút: ${detail.vi}${fragile?.vi ?? ''} ${shown.vi}`,
            en: `${upperFirst(name.en)} passed by a small margin: ${detail.en}${fragile?.en ?? ''} ${shown.en}`,
          }
        : {
            vi: `Chưa đủ tốt để hiện. Trên các năm kiểm tra 2016–2024, mô hình có thời tiết NASA không vượt rõ ràng cùng mô hình bỏ thời tiết: ${detail.vi} Vì vậy Miaudow không hiện dự đoán ${name.vi}, chỉ hiện số liệu thật.`,
            en: `Not good enough to show. On the 2016–2024 test years the model with NASA weather did not clearly beat the same model without weather: ${detail.en} So Miaudow shows no ${name.en} prediction, only real values.`,
          },
    };
  });
}

export const PASSAGES: Passage[] = [...STATIC, ...planPassages(), ...rulePassages(), ...modelPassages()];
