import { useId, useState } from 'react';
import { CLIMATE, CLIMATE_YEARS, climateYear } from '../../data/climate';
import type { SourceRef } from '../../domain/provenance';
import { SourceValue } from '../provenance/SourceValue';
import { useFormat, useT } from '../../app/settings';
import { useWidth } from './useWidth';
import s from './charts.module.css';

const LO = -100,
  HI = 150; // anomaly in % of the monthly normal; the colour saturates beyond these

/** Fill for one month: dry months lean to the drought colour, wet months to the rain colour, normal stays paper. */
function fill(pct: number | null): string {
  if (pct === null) return 'transparent';
  const k = pct < 0 ? Math.min(1, pct / LO) : Math.min(1, pct / HI);
  const c = pct < 0 ? 'var(--data-drought-strong)' : 'var(--data-rain)';
  return `color-mix(in oklab, ${c} ${Math.round(8 + k * 88)}%, var(--bg-sunk))`;
}

/**
 * 34 years × 12 months of rain against the 1991-2020 normal of the same month: each row a year, each square a month.
 * One look shows the dry springs and the wet autumns; a tap on a year opens its numbers, each with its source.
 */
export function RainStrip({
  initialYear = 2010,
  year: controlled,
  onYear,
}: {
  initialYear?: number;
  year?: number;
  onYear?: (y: number) => void;
}) {
  const t = useT();
  const f = useFormat();
  const id = useId();
  const [ref, W] = useWidth<HTMLDivElement>();
  const [own, setOwn] = useState(initialYear);
  const year = controlled ?? own;
  const setYear = (y: number) => {
    setOwn(y);
    onYear?.(y);
  };
  const padL = 58,
    padT = 30,
    rowH = W < 520 ? 13 : 16,
    gap = 2;
  const cw = (W - padL) / 12;
  const H = padT + CLIMATE_YEARS.length * rowH;
  const base = `${CLIMATE.baseline_years[0]}–${CLIMATE.baseline_years[1]}`;

  return (
    <div className={s.strip}>
      <div ref={ref} className={s.stripChart}>
        <svg viewBox={`0 0 ${W} ${H}`} width={W} height={H} className={s.svg} role="img" aria-labelledby={`${id}-t`}>
          <title id={`${id}-t`}>
            {t.climate.stripTitle(CLIMATE_YEARS[0] ?? 0, CLIMATE_YEARS[CLIMATE_YEARS.length - 1] ?? 0)}
          </title>
          {Array.from({ length: 12 }, (_, m) => (
            <text key={m} x={padL + m * cw + cw / 2} y={20} textAnchor="middle" className={s.tick}>
              {m + 1}
            </text>
          ))}
          {CLIMATE_YEARS.map((y, i) => {
            const row = climateYear(y);
            const top = padT + i * rowH;
            const isSel = y === year;
            return (
              <g key={y} className={s.barHit} onClick={() => setYear(y)}>
                <rect x={0} y={top} width={W} height={rowH} fill="transparent" />
                {(y % 5 === 0 || isSel) && (
                  <text x={padL - 10} y={top + rowH - 1} textAnchor="end" className={isSel ? s.tickSel : s.tick}>
                    {y}
                  </text>
                )}
                {row?.anomaly_pct.map((p, m) => (
                  <rect
                    key={m}
                    x={padL + m * cw + gap / 2}
                    y={top + gap / 2}
                    width={cw - gap}
                    height={rowH - gap}
                    rx={2}
                    style={{ fill: fill(p) }}
                    stroke={p === null ? 'var(--line-2)' : 'none'}
                  >
                    <title>
                      {t.climate.monthTip(
                        y,
                        m + 1,
                        p === null
                          ? t.common.noData
                          : `${f.n(row.monthly_rain_mm[m] ?? 0)} mm (${p > 0 ? '+' : ''}${f.n(p)}%)`,
                      )}
                    </title>
                  </rect>
                ))}
                {isSel && (
                  <rect
                    x={padL - 3}
                    y={top}
                    width={W - padL + 3}
                    height={rowH}
                    rx={3}
                    fill="none"
                    stroke="var(--fg)"
                    strokeWidth={1.6}
                  />
                )}
              </g>
            );
          })}
        </svg>
        <div className={s.legend}>
          <span>
            <i className={s.key} style={{ background: fill(-90) }} />
            {t.climate.drier}
          </span>
          <span>
            <i className={s.key} style={{ background: fill(0), border: '1px solid var(--line-2)' }} />
            {t.climate.normal(base)}
          </span>
          <span>
            <i className={s.key} style={{ background: fill(140) }} />
            {t.climate.wetter}
          </span>
        </div>
      </div>

      <div className={s.stripSide}>
        <label className={s.pick}>
          <span>{t.science.year}</span>
          <select value={year} onChange={(e) => setYear(Number(e.target.value))}>
            {CLIMATE_YEARS.map((y) => (
              <option key={y} value={y}>
                {y}
              </option>
            ))}
          </select>
        </label>
        <YearFacts year={year} />
        <p className={s.stripNote}>
          {t.common.notForecast}. {t.climate.gridNote}
        </p>
      </div>
      <StripTable />
    </div>
  );
}

/** The selected year's numbers, each a sourced value (one tap to its source sheet, UI-UX-SPEC H5). */
function YearFacts({ year }: { year: number }) {
  const t = useT();
  const f = useFormat();
  const sel = climateYear(year);
  if (!sel) return null;
  const base = `${CLIMATE.baseline_years[0]}–${CLIMATE.baseline_years[1]}`;
  const normalYear = CLIMATE.normal_mm.farmland_weighted.reduce((a, b) => a + b, 0);
  const derived = (value: string, label: string, detail: string): SourceRef => ({
    sourceId: 'nasa-power',
    kind: 'derived',
    value,
    label,
    detail,
    chain: ['nasa-power', 'modis'],
  });
  return (
    <dl className={s.yearFacts}>
      <dt>{t.climate.annual}</dt>
      <dd>
        <SourceValue
          size="lg"
          {...derived(
            `${f.n(sel.annual_rain_mm ?? 0)} mm`,
            `${t.climate.annual} · ${year}`,
            t.climate.annualDetail(base, f.n(normalYear)),
          )}
        />
      </dd>
      <dt>{t.climate.dryMonths}</dt>
      <dd>
        <SourceValue
          size="lg"
          {...derived(
            String(sel.drought_rain_months.length),
            `${t.climate.dryMonths} · ${year}`,
            t.climate.dryMonthsDetail(base, sel.drought_rain_months.join(', ')),
          )}
        />
      </dd>
      <dt>{t.climate.drySpell}</dt>
      <dd>
        <SourceValue
          size="lg"
          {...derived(
            t.climate.days(f.n(sel.longest_dry_spell_days ?? 0, 0)),
            `${t.climate.drySpell} · ${year}`,
            t.climate.drySpellDetail,
          )}
        />
      </dd>
      <dt>{t.climate.hotDays}</dt>
      <dd>
        <SourceValue
          size="lg"
          {...derived(
            t.climate.days(f.n(sel.hot_days ?? 0, 0)),
            `${t.climate.hotDays} · ${year}`,
            t.climate.hotDaysDetail,
          )}
        />
      </dd>
    </dl>
  );
}

function StripTable() {
  const t = useT();
  const f = useFormat();
  return (
    <div className="visually-hidden">
      <table>
        <caption>{t.climate.stripTitle(CLIMATE_YEARS[0] ?? 0, CLIMATE_YEARS[CLIMATE_YEARS.length - 1] ?? 0)}</caption>
        <thead>
          <tr>
            <th>{t.science.year}</th>
            {Array.from({ length: 12 }, (_, m) => (
              <th key={m}>{m + 1}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {CLIMATE_YEARS.map((y) => (
            <tr key={y}>
              <th scope="row">{y}</th>
              {climateYear(y)?.anomaly_pct.map((p, m) => (
                <td key={m}>{p === null ? '—' : `${f.n(p)}%`}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
