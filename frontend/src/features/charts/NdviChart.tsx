import { useId, useMemo } from 'react';
import ndviJson from '@data/ndvi_modis.json';
import { useFormat, useT } from '../../app/settings';
import { useWidth, yearLabelStep } from './useWidth';
import s from './charts.module.css';

interface Ndvi {
  dates: string[];
  median: (number | null)[];
  p25: (number | null)[];
  p75: (number | null)[];
  n_valid: number[];
  n_total: number[];
}
const NDVI = ndviJson as unknown as Ndvi;

/**
 * MODIS NDVI at Lưu Sơn, 2015-2024: the median of the valid 250 m pixels per 16-day date with the middle half as a
 * band. A date without a valid pixel (cloud) breaks the line instead of being filled. The selected year and the
 * 2020-21 trial season are marked.
 */
export function NdviChart({ year }: { year: number }) {
  const t = useT();
  const f = useFormat();
  const id = useId();
  const [ref, W] = useWidth<HTMLDivElement>();
  const H = 220,
    padL = 52,
    padB = 30,
    padT = 10;
  const t0 = Date.parse(NDVI.dates[0] ?? '2015-01-01'),
    t1 = Date.parse(NDVI.dates[NDVI.dates.length - 1] ?? '2024-12-31');
  const x = (d: string) => padL + ((Date.parse(d) - t0) / (t1 - t0)) * (W - padL - 6);
  const y = (v: number) => padT + (1 - v) * (H - padT - padB);
  const { line, band, gaps } = useMemo(() => {
    const segs: string[] = [];
    const bands: string[] = [];
    let cur: string[] = [];
    let up: string[] = [];
    let lo: string[] = [];
    let missing = 0;
    NDVI.dates.forEach((d, i) => {
      const m = NDVI.median[i],
        a = NDVI.p25[i],
        b = NDVI.p75[i];
      if (m === null || m === undefined || a === null || a === undefined || b === null || b === undefined) {
        missing += 1;
        if (cur.length > 1) {
          segs.push(cur.join(' '));
          bands.push([...up, ...lo.reverse()].join(' '));
        }
        cur = [];
        up = [];
        lo = [];
        return;
      }
      cur.push(`${x(d).toFixed(1)},${y(m).toFixed(1)}`);
      up.push(`${x(d).toFixed(1)},${y(b).toFixed(1)}`);
      lo.push(`${x(d).toFixed(1)},${y(a).toFixed(1)}`);
    });
    if (cur.length > 1) {
      segs.push(cur.join(' '));
      bands.push([...up, ...lo.reverse()].join(' '));
    }
    return { line: segs, band: bands, gaps: missing };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [W]);
  const years = Array.from(new Set(NDVI.dates.map((d) => Number(d.slice(0, 4)))));
  const every = yearLabelStep((W - padL) / years.length);
  return (
    <div className={s.figure} ref={ref}>
      <svg viewBox={`0 0 ${W} ${H}`} width={W} height={H} className={s.svg} role="img" aria-labelledby={`${id}-t`}>
        <title id={`${id}-t`}>{t.climate.ndviTitle}</title>
        <rect
          x={x('2020-06-01')}
          y={padT}
          width={x('2021-06-30') - x('2020-06-01')}
          height={H - padT - padB}
          fill="var(--hl-bg)"
        />
        {years.includes(year) && (
          <rect
            x={x(`${year}-01-01`)}
            y={padT}
            width={x(`${year}-12-31`) - x(`${year}-01-01`)}
            height={H - padT - padB}
            fill="none"
            stroke="var(--fg)"
            strokeDasharray="4 4"
          />
        )}
        {[0, 0.5, 1].map((g) => (
          <g key={g}>
            <line x1={padL} x2={W} y1={y(g)} y2={y(g)} className={s.grid} />
            <text x={padL - 8} y={y(g) + 6} textAnchor="end" className={s.tick}>
              {f.n(g, 1)}
            </text>
          </g>
        ))}
        {band.map((pts, i) => (
          <polygon key={i} points={pts} fill="color-mix(in oklab, var(--c-paddy-500) 22%, transparent)" />
        ))}
        {line.map((pts, i) => (
          <polyline
            key={i}
            points={pts}
            fill="none"
            stroke="var(--c-paddy-600)"
            strokeWidth={2}
            strokeLinejoin="round"
          />
        ))}
        {years
          .filter((yr) => yr % every === 0 || yr === year)
          .map((yr) => (
            <text
              key={yr}
              x={x(`${yr}-07-01`)}
              y={H - 6}
              textAnchor="middle"
              className={yr === year ? s.tickSel : s.tick}
            >
              {yr}
            </text>
          ))}
      </svg>
      <div className={s.legend}>
        <span>
          <i className={s.keyLine} style={{ background: 'var(--c-paddy-600)' }} />
          {t.climate.ndviMedian}
        </span>
        <span>
          <i className={s.key} style={{ background: 'color-mix(in oklab, var(--c-paddy-500) 22%, transparent)' }} />
          {t.climate.ndviBand}
        </span>
        <span>
          <i className={s.key} style={{ background: 'var(--hl-bg)', border: '1px solid var(--line-2)' }} />
          {t.climate.trialSeason}
        </span>
        <span>{t.climate.ndviGaps(gaps, NDVI.dates.length)}</span>
      </div>
    </div>
  );
}
