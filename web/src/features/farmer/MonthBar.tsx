import { bareMonths, formatDayMonth, segments } from '../../domain/calendar';
import { CROPS, type Plan } from '../../domain/plans';
import { usePick, useSettings, useT } from '../../app/settings';
import s from './MonthBar.module.css';

const FAMILY_FILL: Record<string, [string, string]> = {
  rice: ['#d6e8c2', '#557d2c'],
  legume: ['#f2e0b6', '#9a6f14'],
  maize: ['#f5e9a8', '#8a7a10'],
  root: ['#eed3c7', '#a8532f'],
  other: ['#e6d9e7', '#7b5579'],
};
const EN_MONTHS = ['J', 'F', 'M', 'A', 'M', 'J', 'J', 'A', 'S', 'O', 'N', 'D'];

/** Twelve-month field calendar. Overlapping reported dates go on separate lanes instead of hiding each other. */
export function MonthBar({ plan }: { plan: Plan }) {
  const t = useT();
  const pick = usePick();
  const { lang } = useSettings();
  const segs = segments(plan);
  const lanes = Math.max(1, ...segs.map((x) => x.lane + 1));
  const bare = bareMonths(plan);
  return (
    <figure className={s.wrap}>
      <div className={s.bar} style={{ ['--lanes' as string]: lanes }} role="list" aria-label={t.farmer.datesAsReported}>
        {Array.from({ length: 12 }, (_, i) => (
          <span key={i} className={[s.month, bare.includes(i + 1) ? s.bare : ''].join(' ')} aria-hidden="true" />
        ))}
        {segs.map((seg) => {
          const [bg, ink] = FAMILY_FILL[CROPS[seg.crop.crop].family] ?? ['#ddd', '#555'];
          const name = pick(CROPS[seg.crop.crop].name);
          return (
            <span key={seg.crop.key} role="listitem" className={s.seg}
              style={{ left: `${seg.start * 100}%`, width: `${(seg.end - seg.start) * 100}%`, top: `calc(${seg.lane} * (100% / var(--lanes)) + 3px)`, height: `calc(100% / var(--lanes) - 6px)`, background: bg, color: '#16201a', borderColor: ink }}
              title={`${name}: ${formatDayMonth(seg.crop.sow)} → ${seg.crop.harvestNote ?? formatDayMonth(seg.crop.harvest)}`}>
              <span className={s.segName}>{name}</span>
              <span className="visually-hidden">{formatDayMonth(seg.crop.sow)} → {seg.crop.harvestNote ?? formatDayMonth(seg.crop.harvest)}</span>
            </span>
          );
        })}
      </div>
      <div className={s.ticks} aria-hidden="true">
        {Array.from({ length: 12 }, (_, i) => <span key={i}>{lang === 'vi' ? `T${i + 1}` : EN_MONTHS[i]}</span>)}
      </div>
      <figcaption className={s.legend}>
        <span><i className={s.bareKey} />{t.farmer.bare}</span>
        <span>{t.farmer.datesAsReported}</span>
        {lanes > 1 && <span>{t.farmer.overlapNote}</span>}
      </figcaption>
    </figure>
  );
}
