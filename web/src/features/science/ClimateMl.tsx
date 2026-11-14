import { useId } from 'react';
import { analogsOf, anomalyOf, CLIMATE_ML, type Analog, type FeatureDriver, type MethodEvaluation } from '../../data/climateMl';
import { Icon } from '../../design-system/Icon';
import { Reveal } from '../../design-system/Reveal';
import { SourceValue } from '../provenance/SourceValue';
import { useFormat, usePick, useT } from '../../app/settings';
import { useWidth } from '../charts/useWidth';
import charts from '../charts/charts.module.css';
import s from './science.module.css';

const ML = CLIMATE_ML;
const BASE = `${ML.baseline_years[0]}–${ML.baseline_years[1]}`;

/** Climate ML: the closest past years to the chosen one, and which years were unusual, each with its tested verdict. */
export function ClimateMlSection({ year, setYear }: { year: number; setYear: (y: number) => void }) {
  const t = useT();
  const pick = usePick();
  const analogs = analogsOf(year);
  return (
    <section className="band surface-paper" aria-labelledby="ml-title" style={{ paddingTop: 0 }}>
      <div className="container stack" style={{ ['--gap' as string]: 'var(--s-6)' }}>
        <Reveal className={s.colHead}>
          <p className="eyebrow">{t.climateMl.eyebrow}</p>
          <h2 id="ml-title" className="h1">{t.climateMl.title} <span className="num">{year}</span></h2>
          <p className="lead">{t.climateMl.lead(BASE)}</p>
        </Reveal>
        {analogs.length ? (
          <ol className={s.analogs}>
            {analogs.map((a) => <AnalogCard key={a.year} a={a} year={year} onOpen={setYear} />)}
          </ol>
        ) : <p className="muted">{t.common.noData}</p>}
        <p className="muted">{t.climateMl.typical(ML.analogs.median_pairwise_distance)}</p>
        <div className={s.skillGrid}>
          <Reveal className={s.chartCard}>
            <h3 className="h3">{t.climateMl.testedHead}</h3>
            <HitRates ev={ML.analogs.evaluation} />
            <p>{pick(ML.analogs.evaluation.verdict)}</p>
          </Reveal>
          <Reveal className={s.chartCard}>
            <h3 className="h3">{t.climateMl.unusualHead}</h3>
            <p className="muted">{t.climateMl.unusualLead(BASE)}</p>
            <UnusualYears year={year} onYear={setYear} />
          </Reveal>
        </div>
        <details className={s.mlLimits}>
          <summary>{t.climateMl.limits}<Icon name="chevronDown" size={18} /></summary>
          <ul>{[...ML.analogs.limitations, ...ML.anomalies.limitations.slice(2)].map((l) => <li key={l.en}>{pick(l)}</li>)}</ul>
          <p>{pick(ML.anomalies.evaluation.verdict)}</p>
          <p className="mono">{t.climateMl.modelId(ML.model_id, ML.model_version)}</p>
        </details>
      </div>
    </section>
  );
}

function driverText(d: FeatureDriver, year: number, other: number, f: ReturnType<typeof useFormat>, pick: ReturnType<typeof usePick>): string {
  const v = (x: number | null) => (x === null ? '—' : d.unit === '%' ? f.signedPct(x / 100, 0) : `${f.n(x, 0)}`);
  return `${pick(d.label)}: ${year} ${v(d.target_value)} · ${other} ${v(d.other_value)}`;
}

function AnalogCard({ a, year, onOpen }: { a: Analog; year: number; onOpen: (y: number) => void }) {
  const t = useT();
  const f = useFormat();
  const pick = usePick();
  return (
    <li className={s.analog}>
      <p className={s.analogRank}>{t.climateMl.rank(a.order)}</p>
      <p className={s.analogYear}><span className="num">{a.year}</span></p>
      <dl className={s.analogFacts}>
        <dt>{t.climateMl.distance}</dt>
        <dd><SourceValue sourceId="nasa-power" kind="derived" value={f.n(a.distance, 2)} label={`${t.climateMl.distance} · ${year}–${a.year}`}
          detail={t.climateMl.distanceDetail(BASE)} chain={['nasa-power', 'modis']} /></dd>
        <dt>{t.climateMl.yearRain}</dt>
        <dd>{a.annual_rain_anomaly_pct === null ? t.common.noData : f.signedPct(a.annual_rain_anomaly_pct / 100, 0)}</dd>
      </dl>
      <p className={s.analogDiff}><span className="muted">{t.climateMl.differs}</span> {a.drivers.map((d) => driverText(d, year, a.year, f, pick)).join('; ')}</p>
      <button type="button" className={s.analogOpen} onClick={() => onOpen(a.year)}>{t.climateMl.open(a.year)}<Icon name="arrowRight" size={16} /></button>
    </li>
  );
}

/** Three methods, one proxy task, two settings: the share of years each method got right. Labels name each bar. */
function HitRates({ ev }: { ev: MethodEvaluation }) {
  const t = useT();
  const f = useFormat();
  const rows = (prefix: 'proxy' | 'oos') => ([
    ['analog', ev.scores[`${prefix}_analog_k1_tercile`]],
    ['persistence', ev.scores[`${prefix}_persistence_tercile`]],
    ['climatology', ev.scores[`${prefix}_climatology_tercile`]],
  ] as const);
  return (
    <div className={s.hits}>
      {(['proxy', 'oos'] as const).map((p) => (
        <figure key={p} className={s.hitGroup}>
          <figcaption>{t.climateMl.setting[p](ev.n_cases)}</figcaption>
          {rows(p).map(([m, v]) => {
            // the stored rate is rounded to 3 decimals; count the years back so 16/33 shows as 48 %, not 49 %
            const hits = v === null || v === undefined ? null : Math.round(v * ev.n_cases);
            return (
              <div key={m} className={s.hitRow} data-method={m}>
                <span>{t.climateMl.methods[m]}</span>
                <span className={s.hitTrack}><i style={{ width: `${((hits ?? 0) / ev.n_cases) * 100}%` }} /></span>
                <span className="num">{hits === null ? '—' : `${f.pct(hits / ev.n_cases)} · ${hits}/${ev.n_cases}`}</span>
              </div>
            );
          })}
        </figure>
      ))}
    </div>
  );
}

/** 34 years, one bar each: the year's most unusual month in robust units. Bars above the dashed line are flagged. */
function UnusualYears({ year, onYear }: { year: number; onYear: (y: number) => void }) {
  const t = useT();
  const f = useFormat();
  const id = useId();
  const [ref, W] = useWidth<HTMLDivElement>();
  const rows = ML.anomalies.years;
  const max = Math.max(ML.anomalies.threshold, ...rows.map((r) => r.score)) * 1.08;
  const top = 30, padL = 8, padB = 30, H = 230, plotH = H - padB - top;
  const bw = (W - padL) / rows.length;
  const y = (v: number) => top + plotH - (v / max) * plotH;
  const sel = anomalyOf(year);
  // an end-year label is dropped when a flagged year's label sits within two bars of it
  const nearFlag = (i: number) => rows.some((r, j) => r.flagged && j !== i && Math.abs(j - i) <= 2);
  return (
    <div className={s.unusual}>
      <div ref={ref}>
        <svg viewBox={`0 0 ${W} ${H}`} width={W} height={H} className={charts.svg} role="img" aria-labelledby={`${id}-t`}>
          <title id={`${id}-t`}>{t.climateMl.chartTitle(rows[0]?.year ?? 0, rows[rows.length - 1]?.year ?? 0)}</title>
          {rows.map((r, i) => {
            const x = padL + i * bw;
            const isSel = r.year === year;
            return (
              <g key={r.year} className={charts.barHit} onClick={() => onYear(r.year)}>
                <rect x={x} y={top} width={bw} height={plotH} fill="transparent" />
                <rect x={x + 1} y={y(r.score)} width={Math.max(2, bw - 2)} height={top + plotH - y(r.score)} rx={Math.min(4, bw / 3)}
                  style={{ fill: r.flagged ? 'var(--data-heat)' : 'var(--data-cold)', opacity: isSel || r.flagged ? 1 : 0.55 }}
                  stroke={isSel ? 'var(--fg)' : 'none'} strokeWidth={1.6}>
                  <title>{`${r.year}: ${f.n(r.score, 2)}${r.flagged ? ` · ${t.climateMl.flagged}` : ''}`}</title>
                </rect>
                {/* flagged years and the ends are named under the axis; the chosen year is named above its bar */}
                {(r.flagged || ((i === 0 || i === rows.length - 1) && !nearFlag(i))) && !isSel && (
                  <text x={x + bw / 2} y={H - 8} textAnchor="middle" className={charts.tick}>{`’${String(r.year).slice(2)}`}</text>
                )}
                {isSel && (
                  <text x={x + bw / 2} y={y(r.score) - 8} textAnchor="middle" className={charts.tickSel}
                    style={{ paintOrder: 'stroke', stroke: 'var(--bg-raised)', strokeWidth: 5 }}>{r.year}</text>
                )}
              </g>
            );
          })}
          <line x1={padL} x2={W} y1={y(ML.anomalies.threshold)} y2={y(ML.anomalies.threshold)} stroke="var(--fg-2)" strokeDasharray="5 4" strokeWidth={1.4} />
        </svg>
        <div className={charts.legend}>
          <span><i className={charts.key} style={{ background: 'var(--data-heat)' }} />{t.climateMl.flagged}</span>
          <span><i className={charts.key} style={{ background: 'var(--data-cold)', opacity: 0.55 }} />{t.climateMl.notFlagged}</span>
          <span><i className={charts.keyLine} style={{ borderTop: '2px dashed var(--fg-2)' }} />{t.climateMl.threshold(f.n(ML.anomalies.threshold, 2))}</span>
        </div>
      </div>
      {sel && (
        <div className={s.unusualYear} role="status">
          <p><strong className="num">{sel.year}</strong> · {sel.flagged ? t.climateMl.flagged : t.climateMl.notFlagged} · {t.climateMl.score} <span className="num">{f.n(sel.score, 2)}</span></p>
          <ul>
            {sel.driving_months.map((m) => (
              <li key={m.month}>{t.climateMl.month(m.month, m.direction === 'drier', f.n(m.rain_mm, 0), f.n(m.baseline_median_mm, 0))}</li>
            ))}
          </ul>
        </div>
      )}
      <details className={s.mlTable}>
        <summary>{t.climateMl.table}</summary>
        <table>
          <thead><tr><th>{t.science.year}</th><th>{t.climateMl.score}</th><th>{t.climateMl.flagged}</th></tr></thead>
          <tbody>{rows.map((r) => <tr key={r.year}><th scope="row">{r.year}</th><td>{f.n(r.score, 2)}</td><td>{r.flagged ? '✓' : ''}</td></tr>)}</tbody>
        </table>
      </details>
    </div>
  );
}
