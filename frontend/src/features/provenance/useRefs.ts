import { useMemo } from 'react';
import { YEARS, type RuleCode, type RiceSeason } from '../../data';
import { RULES } from '../../domain/hazards';
import { SOURCES } from '../../domain/sources';
import { CROPS, type Plan, type PlanCrop, type TcvnRow } from '../../domain/plans';
import type { SourceRef } from '../../domain/provenance';
import { useFormat, usePick, useSettings } from '../../app/settings';

/** Builds consistent provenance references for every kind of number the app shows. */
export function useRefs() {
  const { lang } = useSettings();
  const pick = usePick();
  const f = useFormat();
  return useMemo(() => {
    const vi = lang === 'vi';
    const cropName = (c: PlanCrop) => `${pick(CROPS[c.crop].name)} ${c.variety}`;
    const span = `${YEARS[0]}–${YEARS[YEARS.length - 1]}`;
    const anyCropWindow = vi
      ? 'thời gian có ít nhất một cây P-02 trên ruộng'
      : 'the time any P-02 crop is in the field';
    const shareDetail = (rule: RuleCode, window: string) => {
      const r = RULES[rule];
      return vi
        ? `${r.article} QĐ 18/2021: “${r.quote}”. Áp cho từng ô NASA POWER trong ${window}; cộng trọng số đất trồng MODIS của các ô đạt ngưỡng. Tính toán của Miaudow, không phải số liệu chính thức.`
        : `${r.article}, Decision 18/2021: “${r.quote}”. Applied to each NASA POWER cell over ${window}; MODIS farmland weights of the cells meeting it are added. Miaudow’s computation, not an official record.`;
    };
    return {
      share(rule: RuleCode, year: number, share: number, crop?: PlanCrop): SourceRef {
        const window = crop
          ? vi
            ? `thời gian ${cropName(crop)} trên ruộng (${crop.sow} → ${crop.harvest}, theo P-02)`
            : `the field time of ${cropName(crop)} (${crop.sow} → ${crop.harvest}, from P-02)`
          : anyCropWindow;
        return {
          sourceId: 'nasa-power',
          kind: 'derived',
          value: f.pct(share),
          label: `${pick(RULES[rule].name)} · ${year}${crop ? ` · ${cropName(crop)}` : ''}`,
          detail: shareDetail(rule, window),
          chain: crop ? ['nasa-power', 'qd18', 'modis', 'p02'] : ['nasa-power', 'qd18', 'modis'],
        };
      },
      /** The source button of a chart or table of yearly shares: the button text is the source's short name. */
      shareSeries(rule: RuleCode): SourceRef {
        return {
          sourceId: 'nasa-power',
          kind: 'derived',
          value: SOURCES['nasa-power'].short,
          label: `${pick(RULES[rule].name)} · ${span}`,
          detail: shareDetail(rule, anyCropWindow),
          chain: ['nasa-power', 'qd18', 'modis'],
        };
      },
      /** Per-cell amounts and rule results of one year (the observatory table). */
      cellTable(rule: RuleCode, year: number): SourceRef {
        return {
          sourceId: 'nasa-power',
          kind: 'derived',
          value: SOURCES['nasa-power'].short,
          label: `${pick(RULES[rule].name)} · ${year}`,
          detail: vi
            ? `Lượng đo của mỗi ô NASA POWER trong năm (${pick(RULES[rule].unit)}); trọng số là phần đất trồng của ô theo bản đồ MODIS. ${shareDetail(rule, anyCropWindow)}`
            : `Each NASA POWER cell’s amount over the year (${pick(RULES[rule].unit)}); the weight is the cell’s farmland share on the MODIS map. ${shareDetail(rule, anyCropWindow)}`,
          chain: ['nasa-power', 'qd18', 'modis'],
        };
      },
      riceSeries(season: RiceSeason): SourceRef {
        return {
          sourceId: 'nso',
          kind: 'data',
          value: SOURCES.nso.short,
          label: vi
            ? `Năng suất lúa Nghệ An so với bình thường, ${span}`
            : `Nghệ An rice yield against normal, ${span}`,
          detail: vi
            ? `Năng suất thật ÷ trung bình 3 năm trước − 1 (vụ ${season === 'spring' ? 'xuân' : season === 'winter' ? 'mùa' : 'hè thu'}).`
            : `Actual yield ÷ mean of the 3 previous years − 1 (${season} season).`,
          chain: ['nso', 'e010'],
        };
      },
      ricePredictionSeries(): SourceRef {
        return {
          sourceId: 'e012',
          kind: 'model',
          value: SOURCES.e012.short,
          label: vi ? 'Dự đoán ngoài mẫu lúa mùa, 2016–2024' : 'Out-of-sample predictions, winter rice, 2016–2024',
          detail: vi
            ? 'Mỗi năm được dự đoán khi mô hình chưa thấy năm đó; vạch là khoảng 80%. Xem lại năm đã qua, không phải dự báo.'
            : 'Each year was predicted before the model had seen it; the line is the 80% range. A look back at past years, not a forecast.',
          chain: ['nasa-power', 'nso', 'e012'],
        };
      },
      ndviSeries(): SourceRef {
        return {
          sourceId: 'modis-ndvi',
          kind: 'data',
          value: SOURCES['modis-ndvi'].short,
          label: vi ? 'Độ xanh NDVI quanh Lưu Sơn' : 'NDVI greenness around Lưu Sơn',
          detail: vi
            ? 'Trung vị và khoảng giữa (phân vị 25–75) của các điểm ảnh 250 m tin cậy ở mỗi ngày 16 ngày; ngày không có điểm ảnh tin cậy để trống.'
            : 'Median and middle half (25th–75th percentile) of the reliable 250 m pixels on each 16-day date; a date without a reliable pixel is left empty.',
        };
      },
      cropProfit(c: PlanCrop): SourceRef {
        return {
          sourceId: 'p02',
          kind: 'study',
          value: `${f.million(c.profit)} ${vi ? 'triệu đ/ha' : 'M VND/ha'}`,
          label: vi ? `Lãi ${cropName(c)}` : `Profit, ${cropName(c)}`,
          detail: vi
            ? `Bảng 13: ${f.n(c.profit)} nghìn đ/ha, đã trừ công. Chi phí ${f.n(c.cost)} nghìn đ/ha; giá bán ${f.n(c.price)} đ/kg lúc thu hoạch.`
            : `Table 13: ${f.n(c.profit)} thousand VND/ha, net of labour. Cost ${f.n(c.cost)} thousand VND/ha; price ${f.n(c.price)} VND/kg at harvest.`,
        };
      },
      planProfit(plan: Plan, total: number): SourceRef {
        const parts = plan.crops.map((c) => f.million(c.profit)).join(' + ');
        return {
          sourceId: 'p02',
          kind: 'derived',
          value: `${f.n(total, 1)} ${vi ? 'triệu đ/ha' : 'M VND/ha'}`,
          label: vi ? 'Lãi cả năm, ba vụ cộng lại' : 'Yearly profit, three seasons added',
          detail: `${parts} = ${f.n(total, 1)} (${vi ? 'Bảng 13, phép cộng của Miaudow' : 'Table 13, Miaudow’s sum'})`,
          chain: ['p02'],
        };
      },
      tcvn(c: PlanCrop, row: TcvnRow): SourceRef {
        const scope = row.scope ? ` · ${pick(row.scope)}` : '';
        return {
          sourceId: 'tcvn8641',
          kind: 'standard',
          value: `${pick(row.value)} m³/ha`,
          label: vi
            ? `Mức tưới ${pick(CROPS[c.crop].name)}${scope}`
            : `Irrigation, ${pick(CROPS[c.crop].name)}${scope}`,
        };
      },
      fao(c: PlanCrop, text: string): SourceRef {
        return {
          sourceId: 'fao-tm3',
          kind: 'standard',
          value: `${text} mm`,
          label: vi
            ? `Nhu cầu nước ${pick(CROPS[c.crop].name)} theo FAO`
            : `FAO water need, ${pick(CROPS[c.crop].name)}`,
        };
      },
      soil(c: PlanCrop, value: string, normal: string): SourceRef {
        return {
          sourceId: 'nasa-power',
          kind: 'derived',
          value,
          label: vi ? `Độ ẩm đất NASA · ${cropName(c)}` : `NASA soil wetness · ${cropName(c)}`,
          detail: vi
            ? `GWETROOT (MERRA-2), trung bình theo trọng số đất trồng trong ${c.sow} → ${c.harvest}; bình thường 1991–2020 = ${normal}. Giá trị mô hình, không phải số đo tại ruộng; không có ngưỡng hay màu đánh giá.`
            : `GWETROOT (MERRA-2), farmland-weighted mean over ${c.sow} → ${c.harvest}; 1991–2020 normal = ${normal}. A model value, not a field measurement; no threshold or rating colour.`,
          chain: ['nasa-power', 'modis', 'p02'],
        };
      },
      rice(season: RiceSeason, year: number, value: number): SourceRef {
        return {
          sourceId: 'nso',
          kind: 'data',
          value: f.signedPct(value),
          label: vi ? `Năng suất lúa Nghệ An ${year} so với bình thường` : `Nghệ An rice yield ${year} against normal`,
          detail: vi
            ? `Năng suất thật ÷ trung bình 3 năm trước − 1 (vụ ${season === 'spring' ? 'xuân' : season === 'winter' ? 'mùa' : 'hè thu'}).`
            : `Actual yield ÷ mean of the 3 previous years − 1 (${season} season).`,
          chain: ['nso', 'e010'],
        };
      },
      ricePrediction(year: number, value: number, low: number, high: number): SourceRef {
        return {
          sourceId: 'e012',
          kind: 'model',
          value: f.signedPct(value),
          label: vi ? `Dự đoán ngoài mẫu lúa mùa ${year}` : `Out-of-sample prediction, winter rice ${year}`,
          detail: vi
            ? `Khoảng 80%: ${f.signedPct(low)} đến ${f.signedPct(high)}. Mô hình chưa thấy năm ${year} khi dự đoán.`
            : `80% range: ${f.signedPct(low)} to ${f.signedPct(high)}. The model had not seen ${year} when predicting.`,
          chain: ['nasa-power', 'nso', 'e012'],
        };
      },
    };
  }, [lang, pick, f]);
}
