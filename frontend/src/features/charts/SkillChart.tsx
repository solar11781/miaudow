import { useId } from 'react';
import type { SkillValue } from '../../data';
import { useFormat } from '../../app/settings';
import { useWidth } from './useWidth';
import s from './charts.module.css';

export interface SkillRow {
  key: string;
  label: string;
  sub?: string;
  skill: SkillValue;
  lead?: boolean;
}

/** Dot-and-interval chart of skill scores around zero (0 = as good as the reference). */
export function SkillChart({ rows, title }: { rows: SkillRow[]; title: string }) {
  const f = useFormat();
  const id = useId();
  const all = rows.flatMap((r) => [r.skill.ci90_low, r.skill.ci90_high]);
  const lo = Math.min(-0.2, Math.floor(Math.min(...all) * 10) / 10);
  const hi = Math.max(0.2, Math.ceil(Math.max(...all) * 10) / 10);
  const [ref, W] = useWidth<HTMLElement>();
  // Wide: labels on the left. Narrow (phones): each label sits above its interval, so 17 px text never collides.
  const stacked = W < 560;
  const labelW = stacked ? 8 : 250,
    padT = 8,
    padB = 32,
    padR = 16;
  const rowH = stacked ? 74 : 54;
  const H = padT + rows.length * rowH + padB;
  const x = (v: number) => labelW + ((v - lo) / (hi - lo)) * (W - labelW - padR);
  const step = hi - lo > 1.2 ? 0.5 : 0.1;
  const ticks: number[] = [];
  for (let v = Math.ceil(lo / step) * step; v <= hi + 1e-9; v += step) ticks.push(Math.round(v * 100) / 100);
  return (
    <figure className={s.figure} ref={ref}>
      <svg viewBox={`0 0 ${W} ${H}`} width={W} height={H} className={s.svg} role="img" aria-labelledby={`${id}-t`}>
        <title id={`${id}-t`}>{title}</title>
        {ticks.map((v) => (
          <g key={v}>
            <line x1={x(v)} x2={x(v)} y1={padT} y2={H - padB} className={v === 0 ? s.zero : s.grid} />
            <text x={x(v)} y={H - 10} textAnchor="middle" className={s.tick}>
              {f.n(v, 1)}
            </text>
          </g>
        ))}
        {rows.map((r, i) => {
          const cy = padT + i * rowH + (stacked ? rowH - 16 : rowH / 2);
          const col = r.lead ? 'var(--data-predicted)' : 'var(--fg-3)';
          return (
            <g key={r.key}>
              <text x={0} y={stacked ? cy - 34 : cy - 4} className={s.label}>
                {r.label}
                {stacked && r.sub ? ` · ${r.sub}` : ''}
              </text>
              {r.sub && !stacked && (
                <text x={0} y={cy + 17} className={s.sub}>
                  {r.sub}
                </text>
              )}
              <line
                x1={x(r.skill.ci90_low)}
                x2={x(r.skill.ci90_high)}
                y1={cy}
                y2={cy}
                stroke={col}
                strokeWidth={r.lead ? 3 : 2}
                strokeLinecap="round"
              />
              <circle cx={x(r.skill.value)} cy={cy} r={r.lead ? 6.5 : 5} fill={col} />
              <title>{`${r.label}: ${f.n(r.skill.value, 3)} (90%: ${f.n(r.skill.ci90_low, 3)} … ${f.n(r.skill.ci90_high, 3)})`}</title>
            </g>
          );
        })}
      </svg>
      <div className="visually-hidden">
        <table>
          <caption>{title}</caption>
          <tbody>
            {rows.map((r) => (
              <tr key={r.key}>
                <th scope="row">{r.label}</th>
                <td>{f.n(r.skill.value, 3)}</td>
                <td>
                  {f.n(r.skill.ci90_low, 3)} – {f.n(r.skill.ci90_high, 3)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </figure>
  );
}
