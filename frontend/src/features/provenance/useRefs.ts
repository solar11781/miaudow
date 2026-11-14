import { useMemo } from 'react';
import type { RuleCode, RiceSeason } from '../../data';
import { RULES } from '../../domain/hazards';
import { CROPS, type Plan, type PlanCrop } from '../../domain/plans';
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
    return {
      share(rule: RuleCode, year: number, share: number, crop?: PlanCrop): SourceRef {
        const r = RULES[rule];
        const window = crop
          ? (vi ? `thời gian ${cropName(crop)} trên ruộng (${crop.sow} → ${crop.harvest}, theo P-02)` : `the field time of ${cropName(crop)} (${crop.sow} → ${crop.harvest}, from P-02)`)
          : (vi ? 'thời gian có ít nhất một cây P-02 trên ruộng' : 'the time any P-02 crop is in the field');
        return {
          sourceId: 'nasa-power', kind: 'derived', value: f.pct(share),
          label: `${pick(r.name)} · ${year}${crop ? ` · ${cropName(crop)}` : ''}`,
          detail: vi
            ? `${r.article} QĐ 18/2021: “${r.quote}”. Áp cho từng ô NASA POWER trong ${window}; cộng trọng số đất trồng MODIS của các ô đạt ngưỡng. Tính toán của Miaudow, không phải số liệu chính thức.`
            : `${r.article}, Decision 18/2021: “${r.quote}”. Applied to each NASA POWER cell over ${window}; MODIS farmland weights of the cells meeting it are added. Miaudow’s computation, not an official record.`,
          chain: crop ? ['nasa-power', 'qd18', 'modis', 'p02'] : ['nasa-power', 'qd18', 'modis'],
        };
      },
      cropProfit(c: PlanCrop): SourceRef {
        return {
          sourceId: 'p02', kind: 'study', value: `${f.million(c.profit)} ${vi ? 'triệu đ/ha' : 'M VND/ha'}`,
          label: vi ? `Lãi ${cropName(c)}` : `Profit, ${cropName(c)}`,
          detail: vi ? `Bảng 13: ${f.n(c.profit)} nghìn đ/ha, đã trừ công. Chi phí ${f.n(c.cost)} nghìn đ/ha; giá bán ${f.n(c.price)} đ/kg lúc thu hoạch.`
            : `Table 13: ${f.n(c.profit)} thousand VND/ha, net of labour. Cost ${f.n(c.cost)} thousand VND/ha; price ${f.n(c.price)} VND/kg at harvest.`,
        };
      },
      planProfit(plan: Plan, total: number): SourceRef {
        const parts = plan.crops.map((c) => f.million(c.profit)).join(' + ');
        return {
          sourceId: 'p02', kind: 'derived', value: `${f.n(total, 1)} ${vi ? 'triệu đ/ha' : 'M VND/ha'}`,
          label: vi ? 'Lãi cả năm, ba vụ cộng lại' : 'Yearly profit, three seasons added',
          detail: `${parts} = ${f.n(total, 1)} (${vi ? 'Bảng 13, phép cộng của Miaudow' : 'Table 13, Miaudow’s sum'})`,
          chain: ['p02'],
        };
      },
      tcvn(c: PlanCrop, text: string): SourceRef {
        return { sourceId: 'tcvn8641', kind: 'standard', value: `${text} m³/ha`, label: vi ? `Mức tưới ${pick(CROPS[c.crop].name)}` : `Irrigation, ${pick(CROPS[c.crop].name)}` };
      },
      fao(c: PlanCrop, text: string): SourceRef {
        return { sourceId: 'fao-tm3', kind: 'standard', value: `${text} mm`, label: vi ? `Nhu cầu nước ${pick(CROPS[c.crop].name)} theo FAO` : `FAO water need, ${pick(CROPS[c.crop].name)}` };
      },
      soil(c: PlanCrop, value: string, normal: string): SourceRef {
        return {
          sourceId: 'nasa-power', kind: 'derived', value,
          label: vi ? `Độ ẩm đất NASA · ${cropName(c)}` : `NASA soil wetness · ${cropName(c)}`,
          detail: vi ? `GWETROOT (MERRA-2), trung bình theo trọng số đất trồng trong ${c.sow} → ${c.harvest}; bình thường 1991–2020 = ${normal}. Giá trị mô hình, không phải số đo tại ruộng; không có ngưỡng hay màu đánh giá.`
            : `GWETROOT (MERRA-2), farmland-weighted mean over ${c.sow} → ${c.harvest}; 1991–2020 normal = ${normal}. A model value, not a field measurement; no threshold or rating colour.`,
          chain: ['nasa-power', 'modis', 'p02'],
        };
      },
      rice(season: RiceSeason, year: number, value: number): SourceRef {
        return {
          sourceId: 'nso', kind: 'data', value: f.signedPct(value),
          label: vi ? `Năng suất lúa Nghệ An ${year} so với bình thường` : `Nghệ An rice yield ${year} against normal`,
          detail: vi ? `Năng suất thật ÷ trung bình 3 năm trước − 1 (vụ ${season === 'spring' ? 'xuân' : season === 'winter' ? 'mùa' : 'hè thu'}).`
            : `Actual yield ÷ mean of the 3 previous years − 1 (${season} season).`,
          chain: ['nso', 'e010'],
        };
      },
      ricePrediction(year: number, value: number, low: number, high: number): SourceRef {
        return {
          sourceId: 'e012', kind: 'model', value: f.signedPct(value),
          label: vi ? `Dự đoán ngoài mẫu lúa mùa ${year}` : `Out-of-sample prediction, winter rice ${year}`,
          detail: vi ? `Khoảng 80%: ${f.signedPct(low)} đến ${f.signedPct(high)}. Mô hình chưa thấy năm ${year} khi dự đoán.` : `80% range: ${f.signedPct(low)} to ${f.signedPct(high)}. The model had not seen ${year} when predicting.`,
          chain: ['nasa-power', 'nso', 'e012'],
        };
      },
    };
  }, [lang, pick, f]);
}
