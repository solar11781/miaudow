import { useState } from 'react';
import { planLabel } from '../../domain/plans';
import { CROPS, PLANS, planProfitMillion, type Plan } from '../../domain/plans';
import { LANDS, type Land } from '../../domain/farmerState';
import { decisionPlan, rulebookPlan } from '../../data/rulebook';
import { Icon } from '../../design-system/Icon';
import { SourceValue } from '../provenance/SourceValue';
import { useRefs } from '../provenance/useRefs';
import { usePick, useT } from '../../app/settings';
import s from './officer.module.css';

/**
 * The officer's evidence desk: one plan at a time, read in the order an officer explains it — conclusion, what it
 * means, the number with its seal, where it is in the source, method and limits, then how it relates to this
 * farmer's field and what to ask. All text comes from the rulebook and the decision core; numbers from the study.
 */
export function EvidenceDesk() {
  const t = useT();
  const pick = usePick();
  const [planId, setPlanId] = useState<Plan['id']>('cc1');
  const [land, setLand] = useState<Land>('canal_end');
  const plan = PLANS.find((p) => p.id === planId) ?? (PLANS[0] as Plan);

  return (
    <div className={s.desk}>
      <div className={s.deskPlans} role="tablist" aria-label={t.officer.deskPick}>
        {PLANS.map((p) => (
          <button
            key={p.id}
            type="button"
            role="tab"
            aria-selected={p.id === planId}
            aria-controls="desk-panel"
            id={`desk-tab-${p.id}`}
            className={s.deskTab}
            onClick={() => setPlanId(p.id)}
          >
            <span className={s.deskTabId}>{planLabel(p, t.farmer)}</span>
            <span>
              {p.textOnly ? pick(p.textOnly.sequence) : p.crops.map((c) => pick(CROPS[c.crop].name)).join(' · ')}
            </span>
          </button>
        ))}
      </div>

      <article id="desk-panel" role="tabpanel" aria-labelledby={`desk-tab-${plan.id}`} className={s.deskPanel}>
        <Ladder plan={plan} />
        <DeskSide plan={plan} land={land} setLand={setLand} />
      </article>
    </div>
  );
}

function Ladder({ plan }: { plan: Plan }) {
  const t = useT();
  const pick = usePick();
  const refs = useRefs();
  const rb = rulebookPlan(plan.id);
  const total = planProfitMillion(plan);
  const seq = plan.textOnly
    ? pick(plan.textOnly.sequence)
    : plan.crops.map((c) => pick(CROPS[c.crop].name)).join(' → ');
  return (
    <ol className={s.ladder}>
      <li>
        <span className={s.step}>{t.officer.ladder[0]}</span>
        <p className={s.conclusion}>{t.officer.conclusion(seq)}</p>
      </li>
      <li>
        <span className={s.step}>{t.officer.ladder[1]}</span>
        <p>{t.officer.meaning}</p>
      </li>
      <li>
        <span className={s.step}>{t.officer.ladder[2]}</span>
        <div className="cluster">
          {total !== null ? (
            <SourceValue size="xl" {...refs.planProfit(plan, total)} />
          ) : (
            plan.textOnly && (
              <SourceValue
                size="lg"
                sourceId="p03"
                kind="study"
                value={pick(plan.textOnly.profitNote)}
                label={t.officer.p03Money}
              />
            )
          )}
        </div>
        {plan.crops.length > 0 && (
          <ul className={s.deskCrops}>
            {plan.crops.map((c) => (
              <li key={c.key}>
                <span>
                  {pick(CROPS[c.crop].name)} {c.variety}
                </span>
                <SourceValue {...refs.cropProfit(c)} />
              </li>
            ))}
          </ul>
        )}
      </li>
      <li>
        <span className={s.step}>{t.officer.ladder[3]}</span>
        <p>{plan.source === 'p02' ? t.officer.whereP02 : t.officer.whereP03}</p>
      </li>
      <li>
        <span className={s.step}>{t.officer.ladder[4]}</span>
        {rb?.why && <p>{pick(rb.why.evidence)}</p>}
        <ul className={s.limits}>
          {(rb?.limitations ?? []).map((l) => (
            <li key={l.vi}>{pick(l)}</li>
          ))}
        </ul>
      </li>
    </ol>
  );
}

function DeskSide({ plan, land, setLand }: { plan: Plan; land: Land; setLand: (l: Land) => void }) {
  const t = useT();
  const pick = usePick();
  const rb = rulebookPlan(plan.id);
  const dp = decisionPlan(plan.id);
  return (
    <aside className={s.deskSide}>
      <div className={s.fitBox}>
        <h3 className="h3">{t.officer.fitTitle}</h3>
        <label className={s.fitPick}>
          <span>{t.officer.fitLabel}</span>
          <select value={land} onChange={(e) => setLand(e.target.value as Land)}>
            {LANDS.filter((l) => l !== 'ask').map((l) => (
              <option key={l} value={l}>
                {t.farmer.lands[l].title}
              </option>
            ))}
          </select>
        </label>
        {dp && <p>{pick(dp.applicability[land] ?? dp.applicability.unknown ?? { vi: '', en: '' })}</p>}
      </div>
      {rb && rb.risk_lines.length > 0 && (
        <div className={s.riskBox}>
          <h3 className="h3">
            <Icon name="alert" size={20} />
            {t.farmer.rows.checks}
          </h3>
          <ul>
            {rb.risk_lines.map((r) => (
              <li key={r.quote}>
                <span>{pick(r.text)}</span>
                <span className={s.riskWhere}>{r.location}</span>
              </li>
            ))}
          </ul>
        </div>
      )}
      {dp && dp.questions_for_officer.length > 0 && (
        <div className={s.askBox}>
          <h3 className="h3">
            <Icon name="user" size={20} />
            {t.officer.askTitle}
          </h3>
          <ol>
            {dp.questions_for_officer.map((q) => (
              <li key={q.vi}>{pick(q)}</li>
            ))}
          </ol>
        </div>
      )}
    </aside>
  );
}
