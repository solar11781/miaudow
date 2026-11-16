import type { CompareResponse, PlanId, Priority } from '../../types';
import { chipLines, planName } from '../../domain/plans';
import { useApiRefs } from '../provenance/useApiRefs';
import { usePick, useT } from '../../app/settings';
import { MoneyLine, PrioTag, WaterLine } from './PlanCard';
import { NumberOr } from './NumberOr';
import s from './farmer.module.css';

/** All six plans side by side before any card is opened (UI-UX-SPEC section 9): in the API's order, with no rank,
 * score or best mark (H3); per plan only the card head's money and water lines and one land fact, the same values and
 * sources as on the card (H5). The long labels are said once above the plans, where the chosen priority's label
 * carries "your priority" in words (H11). A phone has room for two lines per plan: the money line and, when it is
 * water or land, the line of the chosen priority; a wide screen shows all three. */
export function CompareStrip({
  res,
  priority,
  onJump,
}: {
  res: CompareResponse;
  priority: Priority;
  onJump: (id: PlanId) => void;
}) {
  const t = useT();
  const pick = usePick();
  const refs = useApiRefs(res.sources, res.rules);
  const water = priority === 'water' ? undefined : s.stripWide;
  const land = priority === 'land' ? undefined : s.stripWide;
  return (
    <section className={s.strip} aria-labelledby="compare-strip">
      <h2 id="compare-strip" className="h3">
        {t.farmer.stripTitle}
      </h2>
      <p className="small">{t.farmer.comparedWith}</p>
      <ul className={s.stripLegend}>
        <li>
          {priority === 'income' && <PrioTag />}
          {t.farmer.rows.money} · {t.farmer.own.yearSum}
        </li>
        <li className={water}>
          {priority === 'water' && <PrioTag />}
          {t.farmer.summaryWaterLabel}
        </li>
        <li className={land}>
          {priority === 'land' && <PrioTag />}
          {t.farmer.cropsInYear}
        </li>
      </ul>
      <ol className={s.stripList}>
        {res.plans.map((p) => (
          <li key={p.id}>
            <a
              href={`#the-${p.id}`}
              className={s.stripName}
              onClick={(e) => {
                e.preventDefault();
                onJump(p.id);
              }}
            >
              <strong aria-hidden="true">{chipLines(p.id, t.farmer.chip).join(' ')}</strong>
              <span aria-hidden="true">{p.calendar.map((c) => pick(c.crop)).join(' → ')}</span>
              <span className="visually-hidden">
                {planName(p, t.farmer)} · {p.calendar.map((c) => pick(c.crop)).join(' → ')}
              </span>
            </a>
            <MoneyLine plan={p} res={res} refs={refs} brief />
            {/* P-03 money takes off material costs only: never lined up as comparable with P-02 money (section 9) */}
            {p.id === 'usual_p03' && <p className="muted">{t.farmer.definitionPlain.p03}</p>}
            <div className={water}>
              <WaterLine plan={p} refs={refs} brief />
            </div>
            <p className={land}>
              <NumberOr v={p.land.crops_in_year.value} label={t.farmer.cropsInYear} refs={refs} /> ·{' '}
              {p.land.legume.present ? t.farmer.legumeYes : t.farmer.legumeNo}
            </p>
          </li>
        ))}
      </ol>
    </section>
  );
}
