import type { CompareResponse, PlanId, Priority } from '../../types';
import { chipLines, planName } from '../../domain/plans';
import { useApiRefs } from '../provenance/useApiRefs';
import { usePick, useT } from '../../app/settings';
import { MoneyLine, PrioTag, WaterLine } from './PlanCard';
import { NumberOr } from './NumberOr';
import s from './farmer.module.css';

/** All six plans side by side before any card is opened (UI-UX-SPEC section 9): in the API's order, with no rank,
 * score or best mark (H3); per plan only the card head's money and water lines and one land fact, the same values and
 * sources as on the card (H5); the chosen priority's line carries the "your priority" label (H11). */
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
  return (
    <section className={s.strip} aria-labelledby="compare-strip">
      <h2 id="compare-strip" className="h3">
        {t.farmer.stripTitle}
      </h2>
      <p className="small">{t.farmer.comparedWith}</p>
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
            <MoneyLine plan={p} res={res} refs={refs} marked={priority === 'income'} />
            {/* P-03 money takes off material costs only: never lined up as comparable with P-02 money (section 9) */}
            {p.id === 'usual_p03' && <p className="muted">{t.farmer.definitionPlain.p03}</p>}
            <WaterLine plan={p} refs={refs} marked={priority === 'water'} />
            <p>
              {priority === 'land' && <PrioTag />}
              {t.farmer.cropsInYear}:{' '}
              <NumberOr v={p.land.crops_in_year.value} label={t.farmer.cropsInYear} refs={refs} /> ·{' '}
              {p.land.legume.present ? t.farmer.legumeYes : t.farmer.legumeNo}
            </p>
          </li>
        ))}
      </ol>
    </section>
  );
}
