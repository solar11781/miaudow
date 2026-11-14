import type { CompareResponse, Plan, Priority, Value } from '../../types';
import type { ApiRefs } from '../provenance/useApiRefs';
import { usePick, useT } from '../../app/settings';
import { NumberOr } from './NumberOr';
import { SOURCES } from '../../domain/sources';
import s from './PriorityLine.module.css';

// UI-UX-SPEC section 9: only the four tested plans get the line; the two local-practice cards never do
const LINE_PLANS: readonly Plan['id'][] = ['cc1', 'cc2', 'cc3', 'cc4'];

/** The line after the priority label (UI-UX-SPEC section 9, D-136): this plan's value next to the P-02 usual plan's,
 * both from the same response, for income and land; for stability and water a pointer to the usual card's row.
 * Never the P-03 card (D-52), never a verdict. */
export function PriorityLine({
  plan,
  res,
  priority,
  refs,
}: {
  plan: Plan;
  res: CompareResponse;
  priority: Priority;
  refs: ApiRefs;
}) {
  const t = useT();
  const pick = usePick();
  if (!LINE_PLANS.includes(plan.id)) return null;
  const usual = res.plans.find((p) => p.id === 'usual');
  const usualName = usual ? pick(usual.name) : t.common.notAvailable;
  const l = t.farmer.priorityLine;
  // `name` labels the values in the source sheet; it is shown on the line only when the lead does not say it
  const pair = (name: string, mine: Value | null, theirs: Value | null, shown = true) => (
    <p className={s.pair}>
      {shown && <span className={s.name}>{name}:</span>}
      <span className={s.side}>
        {l.thisPlan} <NumberOr v={mine} label={`${name} · ${l.thisPlan}`} refs={refs} />
      </span>
      <span className={s.side}>
        {l.usualPlan} <NumberOr v={theirs} label={`${name} · ${l.usualPlan}`} refs={refs} />
      </span>
    </p>
  );
  return (
    <div className={s.line} data-testid={`card-${plan.id}-priority-line`}>
      {priority === 'income' && (
        <>
          <p>{l.income(usualName, SOURCES.p02.short)}</p>
          {pair(t.farmer.ourSum, plan.money.total, usual?.money.total ?? null, false)}
        </>
      )}
      {priority === 'land' && (
        <>
          <p>{l.land(usualName, SOURCES.p02.short)}</p>
          {pair(t.farmer.cropsInYear, plan.land.crops_in_year.value, usual?.land.crops_in_year.value ?? null)}
          {pair(t.farmer.livingDays, plan.land.living_days.value, usual?.land.living_days.value ?? null)}
        </>
      )}
      {(priority === 'stability' || priority === 'water') && <p>{l.perYear(usualName, SOURCES.p02.short)}</p>}
    </div>
  );
}
