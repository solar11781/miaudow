import type { Plan } from '../types';

/** The study whose money definition a plan uses, by the source ids its money and calendar cite (D-170): P-03 money
 * is "GR - material costs", P-02 money is "GR - TVC". Null when neither study is cited. */
export function moneyStudy(plan: Plan): 'p02' | 'p03' | null {
  const ids = new Set([
    ...plan.money.items.flatMap((i) => i.profit.source_ids),
    ...(plan.money.total?.source_ids ?? []),
    ...plan.calendar.flatMap((c) => c.source_ids),
  ]);
  if (ids.has('R-P03')) return 'p03';
  return ids.has('R-P02') ? 'p02' : null;
}
