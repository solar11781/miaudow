import { useId } from 'react';
import { useFormat } from '../../app/settings';
import { useWidth, yearLabelStep } from './useWidth';
import s from './charts.module.css';

interface Props {
  years: number[];
  values: number[];
  color: string;
  selected?: number;
  onSelect?: (year: number) => void;
  /** Draws a reference line, e.g. at half of the farmland. */
  reference?: number;
  height?: number;
  label: string;
}

/** One bar per year, 0..1 share of farmland. Bars above the reference line are drawn full strength. */
export function YearBars({ years, values, color, selected, onSelect, reference = 0.5, height = 180, label }: Props) {
  const f = useFormat();
  const id = useId();
  const [ref, W] = useWidth<HTMLElement>();
  const H = height,
    padL = 52,
    padB = 30,
    padT = 10,
    padR = 6;
  const bw = (W - padL - padR) / years.length;
  const every = yearLabelStep(bw);
  const y = (v: number) => padT + (1 - v) * (H - padT - padB);
  return (
    <figure className={s.figure} ref={ref}>
      <svg viewBox={`0 0 ${W} ${H}`} width={W} height={H} className={s.svg} role="img" aria-labelledby={`${id}-t`}>
        <title id={`${id}-t`}>{label}</title>
        {[0, 0.5, 1].map((g) => (
          <g key={g}>
            <line x1={padL} x2={W - padR} y1={y(g)} y2={y(g)} className={g === reference ? s.ref : s.grid} />
            <text x={padL - 8} y={y(g) + 6} textAnchor="end" className={s.tick}>
              {f.pct(g)}
            </text>
          </g>
        ))}
        {years.map((yr, i) => {
          const v = values[i] ?? 0;
          const x = padL + i * bw;
          const strong = v > reference;
          const isSel = yr === selected;
          return (
            <g key={yr} className={onSelect ? s.barHit : undefined} onClick={onSelect ? () => onSelect(yr) : undefined}>
              <rect x={x} y={padT} width={bw} height={H - padT - padB} fill="transparent" />
              <rect
                x={x + bw * 0.16}
                y={y(v)}
                width={bw * 0.68}
                height={Math.max(1.5, (H - padT - padB) * v)}
                rx={Math.min(3, bw * 0.2)}
                fill={color}
                opacity={isSel ? 1 : strong ? 0.92 : 0.38}
                className={isSel ? s.sel : undefined}
              />
              {(yr % every === 0 || isSel) && (
                <text x={x + bw / 2} y={H - 6} textAnchor="middle" className={isSel ? s.tickSel : s.tick}>
                  {yr}
                </text>
              )}
              <title>{`${yr}: ${f.pct(v)}`}</title>
            </g>
          );
        })}
      </svg>
      <div className="visually-hidden">
        <table>
          <caption>{label}</caption>
          <tbody>
            {years.map((yr, i) => (
              <tr key={yr}>
                <th scope="row">{yr}</th>
                <td>{f.pct(values[i] ?? 0)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </figure>
  );
}
