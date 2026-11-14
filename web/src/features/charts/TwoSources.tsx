import { useId } from 'react';
import { CLIMATE } from '../../data/climate';
import type { SourceRef } from '../../domain/provenance';
import { SourceValue } from '../provenance/SourceValue';
import { useFormat, useSettings, useT } from '../../app/settings';
import { useWidth } from './useWidth';
import s from './charts.module.css';

interface ChirpsBlock { cells: Record<string, Record<string, (number | null)[]>> }
interface PowerBlock { cells: Record<string, Record<string, { monthly_rain_mm: (number | null)[] }>> }

/**
 * Monthly rain of one NASA POWER cell in one year from two independent products, side by side: NASA POWER (a
 * reanalysis model) and CHIRPS v3 (satellite + station blend, 0.05°, averaged over the cell's Nghệ An pixels).
 * They are never merged; the gap between them is part of the uncertainty.
 */
export function TwoSources({ year, cell }: { year: number; cell: string }) {
  const t = useT();
  const f = useFormat();
  const { lang } = useSettings();
  const id = useId();
  const [ref, W] = useWidth<HTMLDivElement>();
  const raw = CLIMATE as unknown as { chirps: ChirpsBlock | null; series: PowerBlock };
  const power = raw.series.cells[cell]?.[String(year)]?.monthly_rain_mm ?? [];
  const chirps = raw.chirps?.cells[cell]?.[String(year)] ?? [];
  const max = Math.max(50, ...power.map((v) => v ?? 0), ...chirps.map((v) => v ?? 0));
  const H = 240, padL = 56, padB = 30, padT = 10;
  const gw = (W - padL) / 12;
  const y = (v: number) => padT + (1 - v / max) * (H - padT - padB);
  const sum = (a: (number | null)[]) => (a.length === 12 && a.every((v) => v !== null) ? a.reduce<number>((x, v) => x + (v ?? 0), 0) : null);
  const ps = sum(power), cs = sum(chirps);
  const vi = lang === 'vi';
  const refFor = (src: 'power' | 'chirps', v: number): SourceRef => ({
    sourceId: src === 'power' ? 'nasa-power' : 'chirps-v3', kind: 'data', value: `${f.n(v)} mm`,
    label: `${src === 'power' ? 'NASA POWER' : 'CHIRPS v3'} · ${year} · ${cell}`,
    detail: src === 'power'
      ? (vi ? 'Tổng 12 tháng của PRECTOTCORR (mô hình tái phân tích), ô 0,5° × 0,625°. Tháng thiếu ngày thì không cộng.' : 'Sum of 12 months of PRECTOTCORR (reanalysis model), 0.5° × 0.625° cell. Months with a missing day are not summed.')
      : (vi ? 'Tổng 12 tháng của CHIRPS v3 (vệ tinh kết hợp trạm đo, 0,05°), trung bình các điểm ảnh thuộc Nghệ An trong ô. Bản cuối, không dùng bản sơ bộ.' : 'Sum of 12 months of CHIRPS v3 (satellite and station blend, 0.05°), mean of the cell’s Nghệ An pixels. Final product, never the preliminary one.'),
  });
  if (!chirps.length) return <p className="muted">{t.climate.noChirps}</p>;
  return (
    <div className={s.figure} ref={ref}>
      <svg viewBox={`0 0 ${W} ${H}`} width={W} height={H} className={s.svg} role="img" aria-labelledby={`${id}-t`}>
        <title id={`${id}-t`}>{t.climate.twoTitle(year)}</title>
        {[0, 0.5, 1].map((g) => (
          <g key={g}>
            <line x1={padL} x2={W} y1={y(g * max)} y2={y(g * max)} className={s.grid} />
            <text x={padL - 8} y={y(g * max) + 6} textAnchor="end" className={s.tick}>{f.n(g * max)}</text>
          </g>
        ))}
        {Array.from({ length: 12 }, (_, m) => {
          const x = padL + m * gw;
          const bw = Math.max(3, gw * 0.34);
          const pv = power[m] ?? null, cv = chirps[m] ?? null;
          return (
            <g key={m}>
              {pv !== null && <rect x={x + gw * 0.14} y={y(pv)} width={bw} height={H - padB - y(pv)} rx={2} fill="var(--data-rain)"><title>{`NASA POWER ${m + 1}/${year}: ${f.n(pv)} mm`}</title></rect>}
              {cv !== null && <rect x={x + gw * 0.14 + bw + 2} y={y(cv)} width={bw} height={H - padB - y(cv)} rx={2} fill="var(--c-gold-550)"><title>{`CHIRPS v3 ${m + 1}/${year}: ${f.n(cv)} mm`}</title></rect>}
              {(m % (gw < 30 ? 2 : 1) === 0) && <text x={x + gw / 2} y={H - 8} textAnchor="middle" className={s.tick}>{m + 1}</text>}
            </g>
          );
        })}
      </svg>
      <div className={s.legend}>
        <span><i className={s.key} style={{ background: 'var(--data-rain)' }} />NASA POWER</span>
        <span><i className={s.key} style={{ background: 'var(--c-gold-550)' }} />CHIRPS v3</span>
      </div>
      <dl className={s.twoTotals}>
        <div><dt>NASA POWER</dt><dd>{ps !== null ? <SourceValue size="lg" {...refFor('power', ps)} /> : t.common.noData}</dd></div>
        <div><dt>CHIRPS v3</dt><dd>{cs !== null ? <SourceValue size="lg" {...refFor('chirps', cs)} /> : t.common.noData}</dd></div>
      </dl>
      <div className="visually-hidden"><table>
        <caption>{t.climate.twoTitle(year)}</caption>
        <thead><tr><th>{t.science.year}</th><th>NASA POWER</th><th>CHIRPS v3</th></tr></thead>
        <tbody>{Array.from({ length: 12 }, (_, m) => <tr key={m}><th scope="row">{m + 1}</th><td>{power[m] ?? '—'}</td><td>{chirps[m] ?? '—'}</td></tr>)}</tbody>
      </table></div>
    </div>
  );
}
