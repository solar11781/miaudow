import type { ReactNode } from 'react';
import { api, GRID_FIGURE_URL } from '../../api';
import type { Interval, MethodResponse, MetricRow, SeasonCode } from '../../types';
import { COVERAGE_AXES, SEASON_CODES } from '../../types';
import { SkillChart, type SkillRow } from '../charts/SkillChart';
import { useApi } from '../../hooks/useApi';
import { DataLine } from '../provenance/DataLine';
import { LoadState } from '../provenance/LoadState';
import { SourceValue } from '../provenance/SourceValue';
import { useApiRefs, type ApiRefs } from '../provenance/useApiRefs';
import { useFormat, usePick, useT } from '../../app/settings';
import s from '../science/science.module.css';

// metric numbers with 2 decimals (team decision on the method page's display precision, UI-UX-SPEC section 15 item 10)
const DIGITS = 2;
const SKILLS = ['skill_vs_b0', 'skill_vs_b2', 'skill_vs_bnw'] as const;

function Section({ id, title, children }: { id: string; title: string; children: ReactNode }) {
  return (
    <section className="band surface-paper" aria-labelledby={id}>
      <div className="container stack">
        <h2 id={id} className="h1">
          {title}
        </h2>
        {children}
      </div>
    </section>
  );
}

/** Main runs, then each sensitivity code, then spatial holdout (UI-UX-SPEC section 11b item 1), rows in API order. */
function groups(rows: MetricRow[]): [string, MetricRow[]][] {
  const main = rows.filter((r) => r.scheme === 'rolling_origin' && r.sensitivity === null);
  const codes = [
    ...new Set(rows.flatMap((r) => (r.scheme === 'rolling_origin' && r.sensitivity ? [r.sensitivity] : []))),
  ];
  const out: [string, MetricRow[]][] = [
    ['main', main],
    ...codes.map((c): [string, MetricRow[]] => [
      c,
      rows.filter((r) => r.scheme === 'rolling_origin' && r.sensitivity === c),
    ]),
  ];
  out.push(['spatial_holdout', rows.filter((r) => r.scheme === 'spatial_holdout')]);
  return out.filter(([, r]) => r.length > 0);
}

function MetricsTable({ rows, all, refs }: { rows: MetricRow[]; all: MetricRow[]; refs: ApiRefs }) {
  const t = useT();
  const pick = usePick();
  const f = useFormat();
  const num = (v: number | null) => (v === null ? t.common.notAvailable : f.n(v, DIGITS));
  const ci = (v: Interval | null) =>
    v === null
      ? t.common.notAvailable
      : t.method.skillCi(f.n(v.value, DIGITS), f.n(v.ci90_low, DIGITS), f.n(v.ci90_high, DIGITS));
  return (
    <div className={s.tableWrap} tabIndex={0} role="region" aria-label={t.method.metricsTitle}>
      <table className={s.table}>
        <thead>
          <tr>
            {[
              t.method.col.model,
              t.method.col.role,
              t.method.col.subset,
              'RMSE',
              'MAE',
              'R²',
              t.method.col.skillB0,
              t.method.col.skillB2,
              t.method.col.skillBnw,
              t.method.col.coverage80,
              t.method.col.nRows,
              t.method.col.nTestYears,
              t.common.source,
            ].map((h) => (
              <th key={h} scope="col">
                {h}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((r) => {
            const ref = `metric-row-${all.indexOf(r)}`;
            const cells = [
              num(r.rmse),
              num(r.mae),
              num(r.r2_oos),
              ...SKILLS.map((k) => ci(r[k])),
              num(r.coverage_80),
              String(r.n_rows),
              String(r.n_test_years),
            ];
            return (
              <tr key={ref}>
                <th scope="row">
                  {t.science.models[r.model_id]}
                  {r.detail && <span className="muted small"> · {pick(r.detail)}</span>}
                </th>
                <td>{t.method.role[r.role]}</td>
                <td>{t.method.subset(r.subset)}</td>
                {cells.map((c, i) => (
                  <td key={i} className="num" data-value={c} data-source-ref={ref}>
                    {c}
                  </td>
                ))}
                <td data-testid={ref}>
                  <SourceValue
                    {...refs.sources(
                      r.source_ids,
                      t.common.source,
                      `${t.science.models[r.model_id]} · ${t.method.seasons[r.season]}`,
                    )}
                  />
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

function SeasonResults({ season, res, refs }: { season: SeasonCode; res: MethodResponse; refs: ApiRefs }) {
  const t = useT();
  const pick = usePick();
  const rows = res.metrics.filter((m) => m.season === season);
  const gates = res.gates.filter((g) => g.season === season);
  const claim = res.weather_claims.find((c) => c.season === season && c.made);
  const chart = (k: (typeof SKILLS)[number]): SkillRow[] =>
    rows
      .filter(
        (r) =>
          r.scheme === 'rolling_origin' && r.sensitivity === null && r.subset === 'national' && r.role !== 'reference',
      )
      .flatMap((r) => {
        const v = r[k];
        return v
          ? [{ key: `${r.model_id}-${k}`, label: t.science.models[r.model_id], skill: v, lead: r.role === 'primary' }]
          : [];
      });
  return (
    <div className="stack">
      <h3 className="h2">{t.method.seasons[season]}</h3>
      {groups(rows).map(([g, list]) => (
        <div key={g} className="stack">
          <h4 className="h3">
            {g === 'main'
              ? t.method.mainRuns
              : g === 'spatial_holdout'
                ? t.method.spatialHoldout
                : t.method.sensitivity[g as keyof typeof t.method.sensitivity]}
          </h4>
          <MetricsTable rows={list} all={res.metrics} refs={refs} />
        </div>
      ))}
      <h4 className="h3">{t.method.resultsChart}</h4>
      <p className="muted small">{t.method.resultsChartAlt}</p>
      {SKILLS.map((k) => {
        const data = chart(k);
        return data.length ? (
          <SkillChart
            key={k}
            rows={data}
            title={`${t.method.resultsChart} · ${t.method.col[k === 'skill_vs_b0' ? 'skillB0' : k === 'skill_vs_b2' ? 'skillB2' : 'skillBnw']}`}
          />
        ) : null;
      })}
      <ul className={s.reports}>
        {gates.map((g) => (
          <li key={g.gate}>
            <strong>
              {g.gate} · {t.science.gateNames[g.gate]}:{' '}
              {g.passed === null ? t.method.notRun : g.passed ? t.science.passed : t.science.failed}
            </strong>
            <span>{pick(g.detail)}</span>
            {g.gate === 'G4' && g.passed === false && <span>{t.method.rangeHidden}</span>}
          </li>
        ))}
      </ul>
      {claim && <p className={s.notice}>{t.method.weatherClaim}</p>}
    </div>
  );
}

function Method({ res }: { res: MethodResponse }) {
  const t = useT();
  const pick = usePick();
  const refs = useApiRefs(res.sources);
  const seasons = SEASON_CODES.filter((c) => res.metrics.some((m) => m.season === c));
  const rowKeys = [...new Set(res.coverage.map((c) => c.row_key))];
  const rc = res.rain_check;
  return (
    <>
      <Section id="m-model" title={t.method.metricsTitle}>
        <p className="lead">{t.method.question(res.test_years.first, res.test_years.last)}</p>
        {seasons.map((season) => (
          <SeasonResults key={season} season={season} res={res} refs={refs} />
        ))}
        <h3 className="h2">{t.science.reportsTitle}</h3>
        <ul className={s.reports}>
          {res.reports.map((r) => (
            <li key={r.id}>
              <strong>{pick(r.title)}</strong>
              <span>{pick(r.text)}</span>
              <SourceValue {...refs.sources(r.source_ids, t.common.source, pick(r.title))} />
            </li>
          ))}
        </ul>
      </Section>

      <Section id="m-coverage" title={t.method.coverageTitle}>
        <div className={s.tableWrap} tabIndex={0} role="region" aria-label={t.method.coverageTitle}>
          <table className={s.table}>
            <thead>
              <tr>
                <th scope="col">{t.method.col.crop}</th>
                {COVERAGE_AXES.map((a) => (
                  <th key={a} scope="col">
                    {t.method.coverage[a]}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {rowKeys.map((k) => {
                const cells = res.coverage.filter((c) => c.row_key === k);
                return (
                  <tr key={k}>
                    <th scope="row">{cells[0] ? pick(cells[0].crop) : k}</th>
                    {COVERAGE_AXES.map((a) => {
                      const c = cells.find((x) => x.axis === a);
                      return (
                        <td key={a}>
                          {c ? (
                            <>
                              {pick(c.text)}
                              {c.source_ids.length > 0 && (
                                <SourceValue {...refs.sources(c.source_ids, t.common.source, t.method.coverage[a])} />
                              )}
                            </>
                          ) : (
                            '—'
                          )}
                        </td>
                      );
                    })}
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </Section>

      <Section id="m-terms" title={t.method.termsTitle}>
        <ul className={s.reports}>
          {res.explain_terms.map((e) => (
            <li key={e.key}>
              <strong>{pick(e.title)}</strong>
              <span>{pick(e.text)}</span>
              <SourceValue {...refs.sources(e.source_ids, t.common.source, pick(e.title))} />
            </li>
          ))}
        </ul>
      </Section>

      <Section id="m-data" title={t.method.dataTitle}>
        <DataLine sources={res.sources} />
        <p>{t.method.farmland}</p>
        <figure className="stack">
          <img src={GRID_FIGURE_URL} alt={t.method.gridAlt} width={480} height={480} className={s.gridFigure} />
          <figcaption className="muted small">{t.method.gridCaption}</figcaption>
        </figure>
        <h3 className="h2">{t.method.rainCheck}</h3>
        {rc ? (
          <>
            <p>
              {t.method.rainCc} <SourceValue {...refs.value(rc.cc, t.method.rainCc)} />
            </p>
            <p>
              {t.method.meanImerg} <SourceValue {...refs.value(rc.mean_imerg, t.method.meanImerg)} />
            </p>
            <p>
              {t.method.meanPower} <SourceValue {...refs.value(rc.mean_power, t.method.meanPower)} />
            </p>
            <p className="muted small">
              {t.method.rainNotTruth} {t.method.rainGauges}
            </p>
            <details>
              <summary>{t.method.rainTable}</summary>
              <div className={s.tableWrap} tabIndex={0} role="region" aria-label={t.method.rainTable}>
                <table className={s.table}>
                  <thead>
                    <tr>
                      <th scope="col">{t.method.col.month}</th>
                      <th scope="col">IMERG</th>
                      <th scope="col">POWER</th>
                    </tr>
                  </thead>
                  <tbody>
                    {rc.months.map((m) => (
                      <tr key={m.month}>
                        <th scope="row" className="mono">
                          {m.month}
                        </th>
                        <td>
                          <SourceValue {...refs.value(m.imerg, `IMERG · ${m.month}`)} />
                        </td>
                        <td>
                          <SourceValue {...refs.value(m.power, `POWER · ${m.month}`)} />
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </details>
          </>
        ) : (
          <p>{t.method.rainNotRun}</p>
        )}
      </Section>

      <Section id="m-not-used" title={t.method.notUsed}>
        <ul className={s.reports}>
          {res.datasets_not_used.map((d) => (
            <li key={d.dataset}>
              <strong>{d.dataset}</strong>
              <span>{pick(d.reason)}</span>
              <SourceValue {...refs.sources(d.source_ids, t.common.source, d.dataset)} />
            </li>
          ))}
        </ul>
      </Section>

      <Section id="m-limits" title={t.science.limitsTitle}>
        <ul className={s.reports}>
          {res.limitations.map((l) => (
            <li key={l.en}>
              <span>{pick(l)}</span>
            </li>
          ))}
          <li>
            <span>{t.method.noUserTest}</span>
          </li>
        </ul>
      </Section>
    </>
  );
}

/** The method page /phuong-phap (UI-UX-SPEC section 11b): every number comes from GET /api/method. */
export function MethodPage() {
  const t = useT();
  const [res, retry] = useApi(api.method, 'method');
  return (
    <main id="main" className="surface-paper">
      <section className="band surface-paper" aria-labelledby="method-title">
        <div className="container stack">
          <h1 id="method-title" className="display" tabIndex={-1}>
            {t.method.title}
          </h1>
          <p className="lead">{t.method.lead}</p>
        </div>
      </section>
      {res.status === 'ok' ? (
        <Method res={res.data} />
      ) : (
        <div className="container">
          <LoadState state={res} retry={retry} />
        </div>
      )}
    </main>
  );
}
