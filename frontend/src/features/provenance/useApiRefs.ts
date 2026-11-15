import { useMemo } from 'react';
import type { ApiSourceRef } from '../../domain/provenance';
import type { Rule, RuleCode, SourceFacts, SourceId, Value } from '../../types';
import { displayUnit, displayValue } from '../../domain/format';
import { useFormat, usePick, useSettings, useT } from '../../app/settings';

/** Source references for API numbers: the sheet gets the response's own facts for each id (H5). */
export function useApiRefs(sources: Record<SourceId, SourceFacts>, rules?: Rule[]) {
  const pick = usePick();
  const t = useT();
  const { lang } = useSettings();
  const f = useFormat();
  return useMemo(() => {
    const facts = (ids: SourceId[]) => [...new Set(ids)].flatMap((id) => (sources[id] ? [sources[id]] : []));
    // one display of a Value for the cards and the source sheet: the language's digit grouping and the unit as written
    const number = (v: Value) => displayValue(v.value, lang);
    const unit = (v: Value) => displayUnit(pick(v.unit));
    const shown = (v: Value) => `${number(v)} ${unit(v)}`.trim();
    return {
      number,
      unit,
      /** A money Value in thousand dong per ha (P-02) as the farmer reads it, in million dong per ha (D-190); the
       * value as written when it is in another unit. Its source sheet keeps the exact value (`value`). */
      money(v: Value): { number: string; unit: string } {
        const thousands = Number(v.value.replaceAll(',', ''));
        return /^thousand /.test(v.unit.en) && v.value !== '' && Number.isFinite(thousands)
          ? { number: f.million(thousands), unit: t.common.millionPerHa }
          : { number: number(v), unit: unit(v) };
      },
      /** A Value as a source button's props; `note` closes its sheet (the source notes kept off the card, D-187). */
      value(v: Value, label: string, note?: string): ApiSourceRef {
        return { facts: facts(v.source_ids), value: shown(v), label, ...(note ? { note } : {}) };
      },
      /** An official-condition share: the rule text and the "our computation" line go with it (H19). */
      share(rule: RuleCode, v: Value, label: string): ApiSourceRef {
        const r = rules?.find((x) => x.code === rule);
        return {
          facts: facts(v.source_ids),
          value: shown(v),
          label,
          ruleText: r ? pick(r.rule_text) : undefined,
          note: t.common.computedNote,
        };
      },
      /** Sources only (calendar dates, land-care principles, risks): `value` is the text shown on the button. */
      sources(ids: SourceId[], value: string, label: string): ApiSourceRef {
        return { facts: facts(ids), value, label };
      },
    };
  }, [sources, rules, pick, t, lang, f]);
}
export type ApiRefs = ReturnType<typeof useApiRefs>;
