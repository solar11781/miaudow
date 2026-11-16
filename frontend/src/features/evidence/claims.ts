import { useMemo } from 'react';
import { model, YEARS } from '../../data';
import { yearShare } from '../../domain/hazards';
import { lowerFirst, upperFirst } from '../../domain/format';
import { modelVerdict } from '../../domain/rice';
import { CROPS, PLANS, type PlanCrop } from '../../domain/plans';
import type { Bilingual, SourceRef } from '../../domain/provenance';
import { useRefs } from '../provenance/useRefs';
import { useFormat, useSettings } from '../../app/settings';
import { en as enText } from '../../i18n/en';
import { vi as viText } from '../../i18n/vi';

/** What the evidence is, never how it looks (docs/07-ARCHITECTURE-AND-CONTRACTS.md). */
export type Status = 'VERIFIED' | 'DERIVED' | 'ESTIMATED' | 'ILLUSTRATIVE' | 'PENDING_VERIFICATION' | 'UNAVAILABLE';
export const STATUSES: Status[] = [
  'VERIFIED',
  'DERIVED',
  'ESTIMATED',
  'ILLUSTRATIVE',
  'PENDING_VERIFICATION',
  'UNAVAILABLE',
];
export type Topic = 'money' | 'weather' | 'water' | 'model' | 'gaps';
export const TOPICS: Topic[] = ['money', 'weather', 'water', 'model', 'gaps'];

export interface Claim {
  id: string;
  topic: Topic;
  status: Status;
  conclusion: Bilingual;
  meaning: Bilingual;
  refs: SourceRef[];
  location: Bilingual;
  method: Bilingual;
  appliesTo: Bilingual;
  notProve: Bilingual;
}

const crop = (planId: string, key: string): PlanCrop => {
  const c = PLANS.find((p) => p.id === planId)?.crops.find((x) => x.key === key);
  if (!c) throw new Error(`no crop ${key} in plan ${planId}`);
  return c;
};

const TRIAL: Bilingual = {
  vi: 'Một ô 1.000 m² cho mỗi cây, xã Lưu Sơn, Đô Lương, tháng 6/2020 – 6/2021; giá bán lúc thu hoạch năm đó.',
  en: 'One 1,000 m² plot per crop, Luu Son commune, Do Luong, June 2020 – June 2021; sale prices at that harvest.',
};

/** Claims of the evidence library, each built from the same data the rest of the app shows (no copy of a number). */
export function useClaims(): Claim[] {
  const refs = useRefs();
  const f = useFormat();
  const { lang } = useSettings();
  return useMemo(() => {
    const vi = lang === 'vi';
    const peanut = crop('cc1', 'cc1_peanut');
    const rice = crop('cc5', 'cc5_rice');
    const last = YEARS[YEARS.length - 1] as number;
    const drought2010 = yearShare('drought_rain_any2', 2010);
    const heatLast = yearShare('heat', last);
    const skill = (season: 'spring' | 'winter') =>
      model.metrics.find(
        (m) =>
          m.model_id === 'm1_ridge' && m.season === season && m.subset === 'national' && m.scheme === 'rolling_origin',
      )?.skill_vs_bnw ?? null;
    const skillRef = (
      season: 'spring' | 'winter',
      v: { value: number; ci90_low: number; ci90_high: number },
    ): SourceRef => ({
      sourceId: 'e012',
      kind: 'model',
      value: f.n(v.value, 2),
      label: vi
        ? `Điểm hơn kém của mô hình có thời tiết, lúa ${season === 'spring' ? 'xuân' : 'mùa'}`
        : `Skill of the weather model, ${season} rice`,
      detail: vi
        ? `So với mô hình không dùng thời tiết (BNW). 0 = ngang nhau. Khoảng 90%: ${f.n(v.ci90_low, 2)} đến ${f.n(v.ci90_high, 2)}. Kiểm tra ngoài mẫu 2016–2024.`
        : `Against the no-weather twin (BNW). 0 = as good. 90% interval: ${f.n(v.ci90_low, 2)} to ${f.n(v.ci90_high, 2)}. Out-of-sample test 2016–2024.`,
      chain: ['nasa-power', 'nso', 'e012'],
    });

    const claims: Claim[] = [
      {
        id: 'profit-peanut',
        topic: 'money',
        status: 'VERIFIED',
        conclusion: {
          vi: `Trên ô thử nghiệm, lạc L20 vụ xuân 2021 lãi ${f.million(peanut.profit)} triệu đồng mỗi héc-ta.`,
          en: `On the trial plot, L20 peanut in spring 2021 made a profit of ${f.million(peanut.profit)} million VND per hectare.`,
        },
        meaning: {
          vi: 'Đây là kết quả của một ô ruộng trong một năm. Nó cho biết cây lạc từng làm được gì ở đất này, không hứa hẹn lãi trên ruộng nhà bạn.',
          en: 'This is the result of one plot in one year. It shows what peanut once did on this land; it promises nothing for your field.',
        },
        refs: [refs.cropProfit(peanut)],
        location: { vi: 'Trịnh Đức Toàn và cs. (2023), Bảng 13', en: 'Trịnh Đức Toàn et al. (2023), Table 13' },
        method: {
          vi: 'Lãi thuần = tổng thu − tổng chi phí (vật tư, công lao động, năng lượng, lãi vay), như bài báo định nghĩa.',
          en: 'Net profit = gross return − total variable cost (materials, labour, energy, interest), as the paper defines it.',
        },
        appliesTo: TRIAL,
        notProve: {
          vi: 'Không chứng minh lạc sẽ lãi như vậy ở năm khác, giá khác hay ruộng khác; thử nghiệm không lặp lại.',
          en: 'Does not show peanut will earn the same in another year, at other prices or on another field; the trial was not replicated.',
        },
      },
      {
        id: 'profit-rice',
        topic: 'money',
        status: 'VERIFIED',
        conclusion: {
          vi: `Lúa Khang dân, cách làm quen của người dân, lãi ${f.million(rice.profit)} triệu đồng mỗi héc-ta vụ xuân 2021.`,
          en: `Khang dân rice, the farmers' usual practice, made ${f.million(rice.profit)} million VND per hectare in spring 2021.`,
        },
        meaning: {
          vi: 'Con số này là mốc để so các cây khác trong cùng thử nghiệm, cùng năm, cùng cách tính.',
          en: 'This number is the reference for the other crops of the same trial, year and accounting.',
        },
        refs: [refs.cropProfit(rice)],
        location: { vi: 'Trịnh Đức Toàn và cs. (2023), Bảng 13', en: 'Trịnh Đức Toàn et al. (2023), Table 13' },
        method: {
          vi: 'Như trên; cùng bảng, cùng định nghĩa lãi.',
          en: 'As above; same table, same profit definition.',
        },
        appliesTo: TRIAL,
        notProve: {
          vi: 'Không cho biết lúa ở ruộng có nước tưới đủ lãi bao nhiêu; thử nghiệm làm trên đất thường xuyên khô hạn.',
          en: 'Says nothing about rice on well-irrigated fields; the trial land was frequently drought-affected.',
        },
      },
      {
        id: 'drought-2010',
        topic: 'weather',
        status: 'DERIVED',
        conclusion: {
          vi: `Năm 2010, ${f.pct(drought2010)} đất trồng Nghệ An có ít nhất hai tháng mưa thiếu hơn một nửa so với bình thường.`,
          en: `In 2010, ${f.pct(drought2010)} of Nghe An farmland had at least two months with less than half the usual rain.`,
        },
        meaning: {
          vi: 'Đó là một năm thiếu mưa trên phần lớn đất trồng của tỉnh, theo cách đọc ngưỡng hạn của văn bản nhà nước.',
          en: 'It was a dry year over most of the province’s farmland, read with the official drought threshold.',
        },
        refs: [refs.share('drought_rain_any2', 2010, drought2010)],
        location: {
          vi: 'QĐ 18/2021/QĐ-TTg, Điều 48 (ngưỡng); NASA POWER (số mưa)',
          en: 'Decision 18/2021/QĐ-TTg, Art. 48 (threshold); NASA POWER (rain values)',
        },
        method: {
          vi: 'Mưa từng tháng ở mỗi ô lưới NASA so với trung bình 1991–2020 cùng tháng; cộng trọng số đất trồng MODIS của các ô đạt ngưỡng.',
          en: 'Each grid cell’s monthly rain against its 1991–2020 mean for that month; MODIS farmland weights of cells meeting the rule are added.',
        },
        appliesTo: {
          vi: 'Năm ô lưới NASA (mỗi ô khoảng 55 × 66 km) có đất trồng ở Nghệ An.',
          en: 'The five NASA grid cells (about 55 × 66 km each) that hold Nghe An farmland.',
        },
        notProve: {
          vi: 'Không phải số đo tại ruộng, không phải công bố chính thức về hạn hán, và không phải dự báo cho năm sau.',
          en: 'Not a field measurement, not an official drought declaration and not a forecast for next year.',
        },
      },
      {
        id: 'heat-last',
        topic: 'weather',
        status: 'DERIVED',
        conclusion: {
          vi: `Năm ${last}, ${f.pct(heatLast)} đất trồng Nghệ An có đợt nắng nóng từ ba ngày liền trở lên.`,
          en: `In ${last}, ${f.pct(heatLast)} of Nghe An farmland had a heat spell of three days or more.`,
        },
        meaning: {
          vi: 'Nắng nóng theo ngưỡng 35 °C của văn bản nhà nước, trong thời gian có cây trên ruộng thử nghiệm.',
          en: 'Heat by the official 35 °C threshold, during the time the trial crops were in the field.',
        },
        refs: [refs.share('heat', last, heatLast)],
        location: {
          vi: 'QĐ 18/2021/QĐ-TTg, Điều 47; NASA POWER T2M_MAX',
          en: 'Decision 18/2021/QĐ-TTg, Art. 47; NASA POWER T2M_MAX',
        },
        method: {
          vi: 'Từ ba ngày liền có nhiệt độ cao nhất trong cùng một bậc nhiệt của Điều 47.',
          en: 'Three or more consecutive days with the daily maximum inside one band of Art. 47.',
        },
        appliesTo: {
          vi: 'Như trên: năm ô lưới NASA có đất trồng.',
          en: 'As above: the five NASA cells with farmland.',
        },
        notProve: {
          vi: 'Ô lưới làm mờ nhiệt độ cao nhất ở từng nơi; ruộng của bạn có thể nóng hơn hoặc mát hơn.',
          en: 'Grid cells smooth local maxima; your field may be hotter or cooler.',
        },
      },
      {
        id: 'water-rice-peanut',
        topic: 'water',
        status: 'VERIFIED',
        conclusion: {
          vi: 'Theo cùng một tiêu chuẩn Việt Nam, nước phải tưới cho lúa vụ xuân là 6.500–7.500 m³/ha ở Trung bộ (lúa cấy hoặc lúa gieo thẳng) và 6.000–7.000 m³/ha ở Bắc bộ, cho lạc khoảng 2.000 m³/ha.',
          en: 'By the same Vietnamese standard, the water to apply for spring rice is 6,500–7,500 m³/ha in Trung Bo (transplanted or direct-seeded) and 6,000–7,000 m³/ha in Bac Bo, and for peanut about 2,000 m³/ha.',
        },
        meaning: {
          vi: 'Nếu ruộng hay thiếu nước, đây là con số để hỏi cán bộ thủy lợi về lịch tưới.',
          en: 'If your field often lacks water, these are the numbers to raise with the irrigation officer.',
        },
        refs: [...CROPS.rice.tcvn, ...CROPS.peanut.tcvn].map((r, i) =>
          refs.tcvn(i < CROPS.rice.tcvn.length ? rice : peanut, r),
        ),
        location: {
          vi: 'TCVN 8641:2011, bảng mức tưới theo vùng và mùa vụ',
          en: 'TCVN 8641:2011, irrigation tables by region and season',
        },
        method: {
          vi: 'Chép nguyên mức trong tiêu chuẩn; không đổi đơn vị, không so với nguồn khác.',
          en: 'Copied as written in the standard; no unit change, not compared with another source.',
        },
        appliesTo: {
          vi: 'Mức chuẩn cho vùng; tiêu chuẩn không nói Nghệ An thuộc Trung bộ hay Bắc bộ.',
          en: 'Regional norms; the standard does not say whether Nghe An is central or northern.',
        },
        notProve: {
          vi: 'Không phải lượng nước ruộng bạn nhận được; chỉ là nước tưới dưỡng, chưa kể nước làm đất.',
          en: 'Not the water your field receives; maintenance irrigation only, land preparation not included.',
        },
      },
    ];
    // the sentence follows the run's verdict for the season (ML-DESIGN §5b), so a re-run cannot leave it wrong
    for (const season of ['spring', 'winter'] as const) {
      const v = skill(season);
      if (!v) continue;
      const verdict = modelVerdict(season);
      const name = { vi: lowerFirst(viText.science.seasons[season]), en: lowerFirst(enText.science.seasons[season]) };
      const method = {
        vi: 'Kiểm tra ngoài mẫu theo năm (2016–2024): mô hình chỉ thấy các năm trước năm cần dự đoán.',
        en: 'Rolling-origin out-of-sample test (2016–2024): the model only sees years before the predicted one.',
      };
      if (!verdict.weatherHelps) {
        claims.push({
          id: `model-${season}`,
          topic: 'model',
          status: 'DERIVED',
          conclusion: {
            vi: `Thêm thời tiết vào mô hình không giúp dự đoán năng suất ${name.vi} tốt hơn.`,
            en: `Adding weather to the model does not predict ${name.en} yields better.`,
          },
          meaning: {
            vi: `Vì vậy Miaudow không hiện dự đoán ${name.vi}. Một kết quả âm tính cũng là bằng chứng.`,
            en: `So Miaudow shows no ${name.en} prediction. A negative result is evidence too.`,
          },
          refs: [skillRef(season, v)],
          location: {
            vi: 'Thực nghiệm E-012 của nhóm, metrics.json và gates.json',
            en: 'Team experiment E-012, metrics.json and gates.json',
          },
          method,
          appliesTo: {
            vi: 'Năng suất trung bình cả tỉnh, các tỉnh Việt Nam.',
            en: 'Province-average yields, Vietnamese provinces.',
          },
          notProve: {
            vi: 'Không nói thời tiết không ảnh hưởng tới lúa; chỉ nói mô hình này không đo được điều đó tốt hơn mô hình đơn giản.',
            en: 'Does not say weather has no effect on rice; only that this model does not capture it better than the simple one.',
          },
        });
        continue;
      }
      const lookBack = verdict.shown
        ? {
            vi: 'dự đoán chỉ dùng để xem lại các năm đã qua.',
            en: 'predictions are only used to look back at past years.',
          }
        : { vi: lowerFirst(viText.science.modelHidden), en: lowerFirst(enText.science.modelHidden) };
      claims.push({
        id: `model-${season}`,
        topic: 'model',
        status: 'ESTIMATED',
        conclusion: {
          vi: `Với ${name.vi}, mô hình có thời tiết dự đoán tốt hơn một chút so với mô hình không dùng thời tiết.`,
          en: `For ${name.en}, the weather model predicts slightly better than the no-weather model.`,
        },
        // D-165: the narrow, fragile wording belongs to the winter result of report E-018
        meaning:
          season === 'winter'
            ? {
                vi: `${viText.common.winterFragile} (trang Phương pháp, báo cáo E-018); ${lookBack.vi}`,
                en: `${enText.common.winterFragile} (method page, report E-018); ${lookBack.en}`,
              }
            : { vi: upperFirst(lookBack.vi), en: upperFirst(lookBack.en) },
        refs: [skillRef(season, v)],
        location: { vi: 'Thực nghiệm E-012 của nhóm', en: 'Team experiment E-012' },
        method,
        appliesTo: { vi: 'Năng suất trung bình cả tỉnh.', en: 'Province-average yields.' },
        notProve: {
          vi: 'Không phải dự báo vụ tới, không áp cho một thửa ruộng.',
          en: 'Not a forecast of the next season and not valid for one field.',
        },
      });
    }
    claims.push(
      {
        id: 'gap-sentinel',
        topic: 'gaps',
        status: 'UNAVAILABLE',
        conclusion: {
          vi: 'Miaudow chưa có ảnh vệ tinh tách được từng thửa ruộng.',
          en: 'Miaudow has no satellite images that separate individual fields yet.',
        },
        meaning: {
          vi: 'Mọi số thời tiết đang ở mức ô lưới lớn, không phải ở mức thửa ruộng. Ảnh Sentinel-2 20 m của Đô Lương chỉ cho độ xanh theo mùa; mỗi điểm ảnh trộn nhiều thửa ruộng, bờ, đường và nhà.',
          en: 'All weather numbers are at the scale of large grid cells, not of fields. The 20 m Sentinel-2 images of Do Luong show seasonal greenness only; each pixel mixes fields, bunds, roads and houses.',
        },
        refs: [],
        // catalog.json: sentinel2_l2a_do_luong_vi INGESTED (vegetation.json composites, media/sat); nasa_hlss30 and nasa_hlsl30 BLOCKED
        location: {
          vi: 'Sentinel-2 L2A: đã nạp, ảnh NDVI theo mùa 20 m của Đô Lương (2020–21 và 2024), hiện ở Đài quan sát. NASA HLS: bị chặn, cần tài khoản Earthdata.',
          en: 'Sentinel-2 L2A: loaded, seasonal 20 m NDVI composites of Do Luong (2020–21 and 2024), shown on the Earth observatory. NASA HLS: blocked, needs an Earthdata Login.',
        },
        method: {
          vi: 'Cần ranh giới chính xác của khu vực nghiên cứu; geoBoundaries không có lớp ranh giới xã nên Lưu Sơn (cũ) chỉ là một điểm.',
          en: 'Needs an exact study-area boundary; geoBoundaries has no commune layer, so former Luu Son is only a marker point.',
        },
        appliesTo: { vi: 'Cả ứng dụng.', en: 'The whole app.' },
        notProve: {
          vi: 'Chỉ số xanh của ảnh vệ tinh cũng không chẩn đoán được sâu bệnh hay độ ẩm đất.',
          en: 'Even then, a greenness index cannot diagnose pests or soil moisture.',
        },
      },
      {
        id: 'gap-dialect',
        topic: 'gaps',
        status: 'UNAVAILABLE',
        conclusion: {
          vi: 'Chưa có đánh giá nhận dạng giọng nói tiếng Nghệ.',
          en: 'Speech recognition of the Nghe An dialect has not been evaluated.',
        },
        meaning: {
          vi: 'Trợ lý cho nói bằng giọng qua trình duyệt, nhưng luôn cho bạn đọc lại câu trước khi gửi.',
          en: 'The copilot accepts voice through the browser, but always shows you the transcript before sending.',
        },
        refs: [],
        location: {
          vi: 'Khung đo tỉ lệ lỗi từ (WER) đã có; chưa có bản ghi âm có chú thích',
          en: 'A word-error-rate harness exists; no annotated recordings yet',
        },
        method: {
          vi: 'Cần ghi âm thật của bà con, có chép lời, ở nhiều mức tiếng ồn.',
          en: 'Needs real annotated recordings from farmers at several noise levels.',
        },
        appliesTo: { vi: 'Phần trợ lý giọng nói.', en: 'The voice copilot.' },
        notProve: {
          vi: 'Không có con số chính xác nào được công bố cho phần này.',
          en: 'No accuracy figure is claimed for it.',
        },
      },
      {
        id: 'art',
        topic: 'gaps',
        status: 'ILLUSTRATIVE',
        conclusion: {
          vi: 'Các tranh cảnh đồng quê vàng nắng là tranh minh họa, không phải ảnh chụp Nghệ An.',
          en: 'The golden countryside paintings are illustrations, not photographs of Nghe An.',
        },
        meaning: {
          vi: 'Ảnh thật trong ứng dụng luôn ghi tác giả, nơi chụp và giấy phép.',
          en: 'Real photographs in the app always name the author, the place and the licence.',
        },
        refs: [],
        location: {
          vi: 'assets/ASSET_MANIFEST.json và assets/photos/PHOTO_MANIFEST.json',
          en: 'assets/ASSET_MANIFEST.json and assets/photos/PHOTO_MANIFEST.json',
        },
        method: {
          vi: 'Tranh có nhãn "Do AI tạo" trên tranh ở mọi chỗ hiện.',
          en: 'Paintings carry the label “AI-generated” on the picture wherever they appear.',
        },
        appliesTo: { vi: 'Trang chủ và các phần kể chuyện.', en: 'The home page and storytelling sections.' },
        notProve: {
          vi: 'Tranh không mô tả ruộng thử nghiệm hay điều kiện thật.',
          en: 'The paintings do not show the trial fields or real conditions.',
        },
      },
    );
    return claims;
  }, [refs, f, lang]);
}

/** Where the sources disagree or a table looks wrong: kept visible instead of smoothed over (team rulebook). */
export const CONFLICTS: { id: string; title: Bilingual; body: Bilingual; source: Bilingual }[] = [
  {
    id: 'usual-practice',
    title: { vi: 'Hai bài báo, hai “cách làm quen”', en: 'Two papers, two “usual practices”' },
    body: {
      vi: 'Cùng nhóm tác giả, cùng xã Lưu Sơn (cũ): một bài ghi người dân trồng lúa – đậu đen – khoai lang, bài kia ghi lúa – lúa – bỏ hoang. Miaudow hiện cả hai.',
      en: 'Same authors, same commune: one paper records rice – black bean – sweet potato as the usual practice, the other rice – rice – fallow. Miaudow shows both.',
    },
    source: { vi: 'Trịnh Đức Toàn và cs. (2023), hai bài', en: 'Trịnh Đức Toàn et al. (2023), both papers' },
  },
  {
    id: 'table4',
    title: { vi: 'Hai dòng giống hệt nhau ở Bảng 4', en: 'Two identical rows in Table 4' },
    body: {
      vi: 'Dòng đậu xanh (CC1) và dòng đậu đen xanh lòng (CC5) trùng nhau ở mọi cột; bài báo không giải thích. Lãi và chi phí của hai cây này nên đọc thận trọng.',
      en: 'The mung bean row (CC1) and the black bean row (CC5) match in every column; the paper does not explain why. Read these two crops’ money with care.',
    },
    source: { vi: 'Trịnh Đức Toàn và cs. (2023), Bảng 4', en: 'Trịnh Đức Toàn et al. (2023), Table 4' },
  },
  {
    id: 'methods-p44',
    title: { vi: 'Phần phương pháp khác phần kết quả', en: 'Methods text differs from the results' },
    body: {
      vi: 'Trang 44 liệt kê các cơ cấu CC2–CC4 khác với các bảng kết quả. Miaudow theo các bảng kết quả.',
      en: 'Page 44 lists structures CC2–CC4 differently from the results tables. Miaudow follows the results tables.',
    },
    source: { vi: 'Trịnh Đức Toàn và cs. (2023), tr. 44', en: 'Trịnh Đức Toàn et al. (2023), p. 44' },
  },
  {
    id: 'dates',
    title: { vi: 'Ngày gieo trước ngày thu hoạch vụ trước', en: 'Sowing before the previous harvest' },
    body: {
      vi: 'Ở hai chỗ, ngày gieo vụ sau sớm hơn ngày thu hoạch vụ trước. Bài báo không nói cả chuỗi ba vụ có trồng liền trên một thửa hay không.',
      en: 'In two places, a sowing date comes before the previous harvest. The paper does not say whether one field carried the whole three-season sequence.',
    },
    source: { vi: 'Trịnh Đức Toàn và cs. (2023), Bảng 1, 5, 9', en: 'Trịnh Đức Toàn et al. (2023), Tables 1, 5, 9' },
  },
  {
    id: 'profit-defs',
    title: { vi: 'Hai cách tính lãi khác nhau', en: 'Two different profit definitions' },
    body: {
      vi: 'Một bài trừ cả công lao động, bài kia chỉ trừ chi phí vật chất. Miaudow không cộng hay so lãi giữa hai bài.',
      en: 'One paper subtracts labour, the other only material costs. Miaudow never adds or compares profits across the two.',
    },
    source: {
      vi: 'Trịnh Đức Toàn và cs. (2023), hai bài, tr. 3 bài thứ hai',
      en: 'Trịnh Đức Toàn et al. (2023), both papers, p. 3 of the second',
    },
  },
];
