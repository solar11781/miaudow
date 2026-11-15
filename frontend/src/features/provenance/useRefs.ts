import { useMemo } from 'react';
import { YEARS, type RuleCode, type RiceSeason } from '../../data';
import { RULES } from '../../domain/hazards';
import { SOURCES } from '../../domain/sources';
import { CROPS, type Plan, type PlanCrop, type TcvnRow } from '../../domain/plans';
import type { SourceRef } from '../../domain/provenance';
import { useFormat, usePick, useT } from '../../app/settings';

/** Builds consistent provenance references for every kind of number the extras show; all text comes from t.refs. */
export function useRefs() {
  const t = useT();
  const pick = usePick();
  const f = useFormat();
  return useMemo(() => {
    const r = t.refs;
    const cropName = (c: PlanCrop) => `${pick(CROPS[c.crop].name)} ${c.variety}`;
    const span = `${YEARS[0]}–${YEARS[YEARS.length - 1]}`;
    const shareDetail = (rule: RuleCode, window: string) =>
      r.shareDetail(RULES[rule].article, RULES[rule].quote, window);
    return {
      share(rule: RuleCode, year: number, share: number, crop?: PlanCrop): SourceRef {
        const window = crop ? r.cropWindow(cropName(crop), crop.sow, crop.harvest) : r.anyCropWindow;
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
          value: pick(SOURCES['nasa-power'].short),
          label: `${pick(RULES[rule].name)} · ${span}`,
          detail: shareDetail(rule, r.anyCropWindow),
          chain: ['nasa-power', 'qd18', 'modis'],
        };
      },
      /** Per-cell amounts and rule results of one year (the observatory table). */
      cellTable(rule: RuleCode, year: number): SourceRef {
        return {
          sourceId: 'nasa-power',
          kind: 'derived',
          value: pick(SOURCES['nasa-power'].short),
          label: `${pick(RULES[rule].name)} · ${year}`,
          detail: r.cellDetail(pick(RULES[rule].unit), shareDetail(rule, r.anyCropWindow)),
          chain: ['nasa-power', 'qd18', 'modis'],
        };
      },
      riceSeries(season: RiceSeason): SourceRef {
        return {
          sourceId: 'nso',
          kind: 'data',
          value: pick(SOURCES.nso.short),
          label: r.riceSeriesLabel(span),
          detail: r.riceDetail(r.riceSeason[season]),
          chain: ['nso', 'e010'],
        };
      },
      ricePredictionSeries(): SourceRef {
        return {
          sourceId: 'e012',
          kind: 'model',
          value: pick(SOURCES.e012.short),
          label: r.predictionsLabel,
          detail: r.predictionsDetail,
          chain: ['nasa-power', 'nso', 'e012'],
        };
      },
      ndviSeries(): SourceRef {
        return {
          sourceId: 'modis-ndvi',
          kind: 'data',
          value: pick(SOURCES['modis-ndvi'].short),
          label: r.ndviLabel,
          detail: r.ndviDetail,
        };
      },
      cropProfit(c: PlanCrop): SourceRef {
        return {
          sourceId: 'p02',
          kind: 'study',
          value: `${f.million(c.profit)} ${t.common.millionPerHa}`,
          label: r.cropProfitLabel(cropName(c)),
          detail: r.cropProfitDetail(f.n(c.profit), f.n(c.cost), f.n(c.price)),
        };
      },
      planProfit(plan: Plan, total: number): SourceRef {
        const parts = plan.crops.map((c) => f.million(c.profit)).join(' + ');
        return {
          sourceId: 'p02',
          kind: 'derived',
          value: `${f.n(total, 1)} ${t.common.millionPerHa}`,
          label: r.planProfitLabel,
          detail: `${parts} = ${f.n(total, 1)} (${r.planProfitSum})`,
          chain: ['p02'],
        };
      },
      tcvn(c: PlanCrop, row: TcvnRow): SourceRef {
        const scope = row.scope ? ` · ${pick(row.scope)}` : '';
        return {
          sourceId: 'tcvn8641',
          kind: 'standard',
          value: `${pick(row.value)} m³/ha`,
          label: `${r.tcvnLabel(pick(CROPS[c.crop].name))}${scope}`,
        };
      },
    };
  }, [t, pick, f]);
}
