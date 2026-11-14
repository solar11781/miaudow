import { useId } from 'react';
import { YEARS, type RiceSeason } from '../../data';
import { riceYear } from '../../domain/rice';
import { useFormat, useT } from '../../app/settings';
import s from './charts.module.css';

/** Real NSO anomalies as bars around zero; out-of-sample predictions with their 80% range where the season passed. */
export function RiceHistoryChart({ season }: { season: RiceSeason }) {
  const t = useT();
  const f = useFormat();
  const id = useId();
  const rows = YEARS.map((y) => riceYear(season, y));
  const vals = rows.flatMap((r) => [r.actual, r.low80, r.high80]).filter((v): v is number => v !== null);
  const lim = Math.max(0.1, Math.ceil(Math.max(...vals.map(Math.abs)) * 20) / 20);
  const W = 640, H = 240, padL = 40, padR = 8, padT = 10, padB = 28;
  const bw = (W - padL - padR) / YEARS.length;
  const y = (v: number) => padT + ((lim - v) / (2 * lim)) * (H - padT - padB);
  const ticks = [-lim, -lim / 2, 0, lim / 2, lim];
  const hasModel = rows.some((r) => r.predicted !== null);
  const label = `${t.science.riceTitle} · ${t.science.seasons[season]}`;
  return (
    <figure className={s.figure}>
      <svg viewBox={`0 0 ${W} ${H}`} className={s.svg} role="img" aria-labelledby={`${id}-t`}>
        <title id={`${id}-t`}>{label}</title>
        {ticks.map((v) => (
          <g key={v}>
            <line x1={padL} x2={W - padR} y1={y(v)} y2={y(v)} className={v === 0 ? s.zero : s.grid} />
            <text x={padL - 6} y={y(v) + 4} textAnchor="end" className={s.tick}>{f.signedPct(v, 0)}</text>
          </g>
        ))}
        {rows.map((r, i) => {
          const x = padL + i * bw;
          return (
            <g key={r.year}>
              {r.actual !== null && (
                <rect x={x + bw * 0.2} width={bw * 0.6} rx={2}
                  y={Math.min(y(0), y(r.actual))} height={Math.max(1.5, Math.abs(y(r.actual) - y(0)))}
                  fill="var(--data-actual)" opacity={r.actual < 0 ? 1 : 0.55}>
                  <title>{`${r.year}: ${f.signedPct(r.actual)}`}</title>
                </rect>
              )}
              {r.predicted !== null && r.low80 !== null && r.high80 !== null && (
                <g>
                  <line x1={x + bw / 2} x2={x + bw / 2} y1={y(r.high80)} y2={y(r.low80)} stroke="var(--data-predicted)" strokeWidth={2} strokeLinecap="round" />
                  <circle cx={x + bw / 2} cy={y(r.predicted)} r={4.2} fill="var(--bg)" stroke="var(--data-predicted)" strokeWidth={2.2} />
                  <title>{`${r.year}: ${t.science.predicted} ${f.signedPct(r.predicted)} (${f.signedPct(r.low80)} … ${f.signedPct(r.high80)})`}</title>
                </g>
              )}
              {r.year % 5 === 0 && <text x={x + bw / 2} y={H - 8} textAnchor="middle" className={s.tick}>{r.year}</text>}
            </g>
          );
        })}
      </svg>
      <div className={s.legend}>
        <span><i className={s.key} style={{ background: 'var(--data-actual)' }} />{t.science.actual}</span>
        {hasModel && <span><i className={s.keyDot} style={{ border: '2px solid var(--data-predicted)' }} />{t.science.predicted}</span>}
        {hasModel && <span><i className={s.keyLine} style={{ background: 'var(--data-predicted)' }} />{t.science.interval}</span>}
      </div>
      <div className="visually-hidden"><table>
        <caption>{label}</caption>
        <thead><tr><th>{t.science.year}</th><th>{t.science.actual}</th><th>{t.science.predicted}</th></tr></thead>
        <tbody>
          {rows.map((r) => (
            <tr key={r.year}><th scope="row">{r.year}</th><td>{r.actual === null ? '—' : f.signedPct(r.actual)}</td><td>{r.predicted === null ? '—' : f.signedPct(r.predicted)}</td></tr>
          ))}
        </tbody>
      </table></div>
    </figure>
  );
}
