import { dateRange, periodPieces, spanSegments } from '../../domain/calendar';
import type { Plan } from '../../types';
import { SourceValue } from '../provenance/SourceValue';
import type { ApiRefs } from '../provenance/useApiRefs';
import { usePick, useT } from '../../app/settings';
import s from './MonthBar.module.css';

const FAMILY_FILL: Record<string, [string, string]> = {
  rice: ['#d6e8c2', '#557d2c'],
  legume: ['#f2e0b6', '#9a6f14'],
  maize: ['#f5e9a8', '#8a7a10'],
  root: ['#eed3c7', '#a8532f'],
  other: ['#e6d9e7', '#7b5579'],
};
// colour group of each API crop id; the crop name is always written next to the colour (H11)
export const CROP_FAMILY: Record<string, keyof typeof FAMILY_FILL> = {
  rice: 'rice',
  black_bean: 'legume',
  mung_bean: 'legume',
  peanut: 'legume',
  soybean: 'legume',
  maize_grain: 'maize',
  maize_biomass: 'maize',
  sweet_potato: 'root',
  pumpkin: 'root',
  chili: 'other',
  black_sesame: 'other',
};

const fill = (cropId: string) => FAMILY_FILL[CROP_FAMILY[cropId] ?? 'other'] ?? ['#ddd', '#555'];

/** Twelve-month field calendar from the API plan (UI-UX-SPEC section 9a). Overlapping reported dates go on separate
 * lanes; bare periods are the engine's, hatched and labelled; every date opens the plan's calendar sources (H5). */
export function MonthBar({ plan, refs }: { plan: Plan; refs: ApiRefs }) {
  const t = useT();
  const pick = usePick();
  const segs = spanSegments(plan.calendar);
  const lanes = Math.max(1, ...segs.map((x) => x.lane + 1));
  const ids = plan.calendar.flatMap((c) => c.source_ids);
  return (
    <figure className={s.wrap}>
      <div className={s.bar} style={{ ['--lanes' as string]: lanes }} aria-hidden="true">
        {Array.from({ length: 12 }, (_, i) => (
          <span key={i} className={s.month} />
        ))}
        {plan.bare_periods.flatMap((p) =>
          periodPieces(p).map((piece) => (
            <span
              key={`${p.from}-${piece.start}`}
              className={s.bare}
              style={{ left: `${piece.start * 100}%`, width: `${(piece.end - piece.start) * 100}%` }}
            />
          )),
        )}
        {segs.map((seg, i) => {
          const [bg, ink] = fill(seg.span.crop_id);
          return (
            <span
              key={seg.span.crop_key}
              className={s.seg}
              style={{
                left: `${seg.start * 100}%`,
                width: `${(seg.end - seg.start) * 100}%`,
                top: `calc(${seg.lane} * (100% / var(--lanes)) + 3px)`,
                height: `calc(100% / var(--lanes) - 6px)`,
                background: bg,
                color: '#16201a',
                borderColor: ink,
              }}
            >
              {/* a crop name does not fit a short lane, so the lane carries its line's number in the list below */}
              {i + 1}
            </span>
          );
        })}
      </div>
      <div className={s.ticks} aria-hidden="true">
        {Array.from({ length: 12 }, (_, i) => (
          <span key={i}>{i + 1}</span>
        ))}
      </div>
      <p className={s.axis} aria-hidden="true">
        {t.farmer.monthAxis}
      </p>
      <ul className={s.dates} aria-label={t.farmer.datesAsReported}>
        {segs.map(({ span }, i) => {
          const [bg, ink] = fill(span.crop_id);
          const shown = `${dateRange(span.sow_from ?? '', span.sow_to ?? '')} → ${dateRange(span.harvest_from ?? '', span.harvest_to ?? '')}`;
          const name = [pick(span.crop), span.variety ? pick(span.variety) : ''].filter(Boolean).join(' ');
          return (
            <li key={span.crop_key}>
              <span>
                <i className={s.key} style={{ background: bg, borderColor: ink }} aria-hidden="true">
                  {i + 1}
                </i>
                {name}
              </span>
              <SourceValue {...refs.sources(span.source_ids, shown, `${name} · ${t.farmer.datesAsReported}`)} />
            </li>
          );
        })}
        {plan.bare_periods.map((p) => {
          const shown = dateRange(p.from, p.to);
          return (
            <li key={p.from}>
              <span>
                <i className={s.bareKey} aria-hidden="true" />
                {t.farmer.bare}
              </span>
              <SourceValue {...refs.sources(ids, shown, t.farmer.bare)} />
            </li>
          );
        })}
      </ul>
      <figcaption className={s.legend}>
        <span>{t.farmer.datesAsReported}</span>
        {lanes > 1 && <span>{t.farmer.overlapNote}</span>}
      </figcaption>
    </figure>
  );
}
