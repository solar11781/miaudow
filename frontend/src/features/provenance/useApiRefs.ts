import { useMemo } from 'react';
import type { ApiSourceRef } from '../../domain/provenance';
import type { Rule, RuleCode, SourceFacts, SourceId, Value } from '../../types';
import { usePick, useT } from '../../app/settings';

/** Source references for API numbers: the sheet gets the response's own facts for each id (H5). */
export function useApiRefs(sources: Record<SourceId, SourceFacts>, rules?: Rule[]) {
  const pick = usePick();
  const t = useT();
  return useMemo(() => {
    const facts = (ids: SourceId[]) => [...new Set(ids)].flatMap((id) => (sources[id] ? [sources[id]] : []));
    const shown = (v: Value) => `${v.value} ${pick(v.unit)}`.trim();
    return {
      shown,
      /** A Value as a source button's props. */
      value(v: Value, label: string): ApiSourceRef {
        return { facts: facts(v.source_ids), value: shown(v), label };
      },
      /** An official-condition share: the rule text and the "our computation" line go with it (H19). */
      share(rule: RuleCode, v: Value, label: string): ApiSourceRef {
        const r = rules?.find((x) => x.code === rule);
        return { facts: facts(v.source_ids), value: shown(v), label, ruleText: r ? pick(r.rule_text) : undefined, note: t.common.computedNote };
      },
      /** Sources only (calendar dates, land-care principles, risks): `value` is the text shown on the button. */
      sources(ids: SourceId[], value: string, label: string): ApiSourceRef {
        return { facts: facts(ids), value, label };
      },
    };
  }, [sources, rules, pick, t]);
}
export type ApiRefs = ReturnType<typeof useApiRefs>;
