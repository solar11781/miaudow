import { lazy, Suspense, useCallback, useEffect, useMemo, useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { geo, hazards, model, YEARS, type MetricRow, type RiceSeason, type RuleCode } from '../../data';
import { cellMagnitude, cellMet, RULES, yearShare } from '../../domain/hazards';
import { Icon } from '../../design-system/Icon';
import { Reveal } from '../../design-system/Reveal';
// three.js arrives in its own chunk after the page's text and numbers are on screen
const Observatory3D = lazy(() => import('./Observatory3D').then((m) => ({ default: m.Observatory3D })));
import { YearBars } from '../charts/YearBars';
import { RiceHistoryChart } from '../charts/RiceHistoryChart';
import { SkillChart, type SkillRow } from '../charts/SkillChart';
import { SourceValue } from '../provenance/SourceValue';
import { ClimateMlSection } from './ClimateMl';
import { useRefs } from '../provenance/useRefs';
import { useFormat, usePick, useSettings, useT } from '../../app/settings';
import { RainStrip } from '../charts/RainStrip';
import { TwoSources } from '../charts/TwoSources';
import { NdviChart } from '../charts/NdviChart';
import s from './science.module.css';

const SCIENCE_RULES: RuleCode[] = ['drought_rain_any2', 'drought_rain_consecutive', 'heat', 'heavy_rain', 'cold'];
type Subset = 'national' | 'na_ht_th' | 'nghe_an';
const SUBSET_KEY: Record<Subset, string> = { national: 'national', na_ht_th: 'na_ht_th', nghe_an: 'unit:Nghe An' };

function GridSection({ year, setYear }: { year: number; setYear: (y: number) => void }) {
  const t = useT();
  const pick = usePick();
  const f = useFormat();
  const refs = useRefs();
  const { calm, lang } = useSettings();
  const [rule, setRule] = useState<RuleCode>('drought_rain_any2');
  const [cell, setCell] = useState<string>(hazards.cells.reduce((a, b) => (b.weight > a.weight ? b : a)).id);
  const [playing, setPlaying] = useState(false);

  useEffect(() => {
    if (!playing) return;
    const id = window.setInterval(() => setYear(year >= (YEARS[YEARS.length - 1] as number) ? (YEARS[0] as number) : year + 1), 1100);
    return () => window.clearInterval(id);
  }, [playing, year, setYear]);

  const share = yearShare(rule, year);
  const info = RULES[rule];
  const sel = geo.grid.find((c) => c.id === cell);

  return (
    <section className={`band surface-forest grain ${s.gridBand}`} aria-labelledby="grid-title">
      <div className="container stack" style={{ ['--gap' as string]: 'var(--s-6)' }}>
        <header className={s.pageHead}>
          <p className="eyebrow">{t.science.eyebrow}</p>
          <h1 className={`display ${s.pageTitle}`}>{t.science.title}</h1>
          <p className="lead">{t.science.lead}</p>
          <Link to={`/dai-quan-sat?canh=analysis&nam=${year}`} className={s.globeLink}><Icon name="globe" size={20} />{t.science.globeCta}<Icon name="arrowRight" size={18} /></Link>
        </header>

        <div className={s.rules} role="radiogroup" aria-label={t.science.rule}>
          {SCIENCE_RULES.map((r) => (
            <button key={r} type="button" role="radio" aria-checked={rule === r} className={s.ruleBtn} onClick={() => setRule(r)}>
              <i style={{ background: RULES[r].color }} aria-hidden="true" />{pick(RULES[r].name)}<span className={s.article}>{RULES[r].article}</span>
            </button>
          ))}
        </div>

        <p className={s.panelLead}>{t.science.mapLead}</p>
        <div className={s.observatory}>
          <div className={s.stageCol}>
            <h2 id="grid-title" className="visually-hidden">{t.science.mapTitle}</h2>
            <Suspense fallback={<div className={s.stagePlaceholder} role="status">{t.common.loading}</div>}>
              <Observatory3D rule={rule} year={year} selected={cell} onSelect={setCell} />
            </Suspense>
          </div>

          <aside className={s.side} aria-label={t.science.readingFor(year)}>
            <div className={s.kpi}>
              <p className={s.kpiLabel}>{pick(info.name)} · {info.article} · <span className="num">{year}</span></p>
              <SourceValue size="xl" {...refs.share(rule, year, share)} />
              <p className={s.kpiSub}>{t.science.shareOfFarmland}</p>
              <p className={s.quote}>“{info.quote}”</p>
              <p className={s.computed}>{pick(info.computed)}</p>
              <p className={s.notForecast}>{t.common.notForecast}</p>
            </div>
            {sel && (
              <dl className={s.cellCard}>
                <dt>{t.science.cell}</dt><dd className="mono">{sel.lat.toFixed(1)}°N {sel.lon.toFixed(3)}°E</dd>
                <dt>{t.science.weight}</dt><dd className="mono">{f.pct(sel.weight, 1)}</dd>
                <dt>{t.science.measured}</dt><dd className="mono">{f.n(cellMagnitude(info.magnitude, sel.id, year), 1)} {info.unit[lang]}</dd>
                <dt>{t.science.ruleMet}</dt><dd>{cellMet(rule, sel.id, year) ? t.science.met : t.science.notMet}</dd>
              </dl>
            )}
          </aside>
        </div>

        <div className={s.timelineCard}>
          <div className={s.timelineHead}>
            <p className={s.timelineTitle}>{pick(info.name)} · {t.science.shareOfFarmland}, {YEARS[0]}–{YEARS[YEARS.length - 1]}</p>
            <label className={s.yearSelect}>
              <span>{t.science.year}</span>
              <select value={year} onChange={(e) => { setPlaying(false); setYear(Number(e.target.value)); }}>
                {YEARS.map((y) => <option key={y} value={y}>{y}</option>)}
              </select>
            </label>
          </div>
          <div className={s.timeline}>
            <button type="button" className={s.play} onClick={() => setPlaying((p) => !p)} aria-pressed={playing} disabled={calm && !playing}
              aria-label={playing ? t.science.pause : t.science.play}>
              <Icon name={playing ? 'pause' : 'play'} size={18} />
            </button>
            <div className={s.bars}>
              <YearBars years={YEARS} values={hazards.year_level[rule]} color={info.color} selected={year}
                onSelect={(y) => { setPlaying(false); setYear(y); }} height={150} label={`${pick(info.name)} · ${t.science.shareOfFarmland}`} />
            </div>
          </div>
        </div>

        <div className={s.tableWrap} tabIndex={0} role="region" aria-label={t.science.tableCaption}>
          <table className={s.table}>
            <caption>{t.science.tableCaption} · {pick(info.name)} · {year}</caption>
            <thead><tr><th scope="col">{t.science.cell}</th><th scope="col">{t.science.weight}</th><th scope="col">{t.science.measured}</th><th scope="col">{t.science.ruleMet}</th></tr></thead>
            <tbody>
              {hazards.cells.map((c) => (
                <tr key={c.id} aria-selected={c.id === cell} onClick={() => setCell(c.id)}>
                  <th scope="row" className="mono">{c.lat.toFixed(1)}°N {c.lon.toFixed(3)}°E</th>
                  <td className="num">{f.pct(c.weight, 1)}</td>
                  <td className="num">{f.n(cellMagnitude(info.magnitude, c.id, year), 1)}</td>
                  <td>{cellMet(rule, c.id, year) ? <span className={s.yes}>{t.science.yes}</span> : <span className={s.no}>{t.science.no}</span>}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </section>
  );
}


const CELLS = ['19.0_105.0', '19.0_105.625', '18.5_105.625', '19.5_105.0', '19.5_105.625'];

/** One shared year: the rain strip, the two rain sources and the greenness follow the observatory's year. */
function ClimateSection({ year, setYear }: { year: number; setYear: (y: number) => void }) {
  const t = useT();
  const [cell, setCell] = useState(CELLS[0] as string);
  const q = new URLSearchParams({ q: t.climate.askYearQ(year), hoi: '1' }).toString();
  return (
    <section className="band surface-paper" aria-labelledby="climate-title">
      <div className="container stack" style={{ ['--gap' as string]: 'var(--s-8)' }}>
        <Reveal className={s.colHead}>
          <p className="eyebrow">{t.climate.sectionEyebrow}</p>
          <h2 id="climate-title" className="h1">{t.climate.sectionTitle} · <span className="num">{year}</span></h2>
          <p className="lead">{t.climate.sectionLead}</p>
          <Link className={s.askLink} to={`/tro-ly?${q}`} viewTransition><Icon name="spark" size={18} />{t.climate.askYear(year)}</Link>
        </Reveal>
        <Reveal className={s.chartCard}><RainStrip year={year} onYear={setYear} /></Reveal>
        <div className={s.skillGrid}>
          <Reveal className={s.chartCard}>
            <h3 className="h3">{t.climate.twoHead}</h3>
            <p className="muted">{t.climate.twoLead}</p>
            <label className={s.yearSelect}>
              <span>{t.climate.cellLabel}</span>
              <select value={cell} onChange={(e) => setCell(e.target.value)}>
                {CELLS.map((c) => <option key={c} value={c}>{c.replace('_', '°N ')}°E</option>)}
              </select>
            </label>
            <TwoSources year={year} cell={cell} />
          </Reveal>
          <Reveal className={s.chartCard}>
            <h3 className="h3">{t.climate.ndviHead}</h3>
            <p className="muted">{t.climate.ndviLead}</p>
            <NdviChart year={year} />
          </Reveal>
        </div>
      </div>
    </section>
  );
}

function RiceSection() {
  const t = useT();
  const [season, setSeason] = useState<RiceSeason>('winter');
  const status = model.seasons.find((x) => x.season === season)?.model_status;
  return (
    <section className="band surface-paper" aria-labelledby="rice-title">
      <div className={`container ${s.twoCol}`}>
        <Reveal className={s.colHead}>
          <h2 id="rice-title" className="h1">{t.science.riceTitle}</h2>
          <p className="lead">{t.science.riceLead}</p>
          <div className={s.seg} role="radiogroup" aria-label={t.science.riceTitle}>
            {(['spring', 'summer_autumn', 'winter'] as RiceSeason[]).map((x) => (
              <button key={x} type="button" role="radio" aria-checked={season === x} onClick={() => setSeason(x)}>{t.science.seasons[x]}</button>
            ))}
          </div>
          {status !== 'shown' && <p className={s.notice}><Icon name="alert" size={18} />{status === 'not_shown' ? t.science.modelHidden : t.science.notModeled}</p>}
        </Reveal>
        <Reveal className={s.chartCard}><RiceHistoryChart season={season} /></Reveal>
      </div>
    </section>
  );
}

function SkillSection() {
  const t = useT();
  const pick = usePick();
  const [subset, setSubset] = useState<Subset>('national');
  const rows = (season: RiceSeason): SkillRow[] => {
    const get = (id: MetricRow['model_id']) => model.metrics.find((m) => m.model_id === id && m.season === season && m.subset === SUBSET_KEY[subset] && m.scheme === 'rolling_origin');
    const out: SkillRow[] = [];
    for (const id of ['m1_ridge', 'm2_lgbm', 'm3_rf', 'bnw', 'b2'] as const) {
      const m = get(id);
      if (m?.skill_vs_b0) out.push({ key: `${season}-${id}`, label: t.science.models[id], sub: `MAE ${m.mae.toFixed(3)} · n=${m.n_rows}`, skill: m.skill_vs_b0, lead: id === 'm1_ridge' });
    }
    return out;
  };
  const bnwRows: SkillRow[] = (['spring', 'winter'] as RiceSeason[]).flatMap((season) => {
    const m = model.metrics.find((x) => x.model_id === 'm1_ridge' && x.season === season && x.subset === SUBSET_KEY[subset] && x.scheme === 'rolling_origin');
    return m?.skill_vs_bnw ? [{ key: `bnw-${season}`, label: t.science.seasons[season], sub: 'M1 vs BNW', skill: m.skill_vs_bnw, lead: true }] : [];
  });
  const gates = useMemo(() => model.gates, []);
  return (
    <section className="band surface-paper" aria-labelledby="skill-title" style={{ paddingTop: 0 }}>
      <div className="container stack" style={{ ['--gap' as string]: 'var(--s-8)' }}>
        <Reveal className={s.colHead}>
          <h2 id="skill-title" className="h1">{t.science.skillTitle}</h2>
          <p className="lead">{t.science.skillLead}</p>
          <div className={s.seg} role="radiogroup" aria-label={t.science.skillTitle}>
            {(['national', 'na_ht_th', 'nghe_an'] as Subset[]).map((x) => (
              <button key={x} type="button" role="radio" aria-checked={subset === x} onClick={() => setSubset(x)}>{t.science.subsets[x]}</button>
            ))}
          </div>
        </Reveal>
        <div className={s.skillGrid}>
          {(['spring', 'winter'] as RiceSeason[]).map((season) => (
            <Reveal key={season} className={s.chartCard}>
              <h3 className="h3">{t.science.seasons[season]}</h3>
              <SkillChart rows={rows(season)} title={`${t.science.skillTitle} · ${t.science.seasons[season]}`} />
            </Reveal>
          ))}
        </div>
        <Reveal className={s.chartCard}>
          <h3 className="h3">{t.science.skillVsBnw}</h3>
          <SkillChart rows={bnwRows} title={t.science.skillVsBnw} />
          <ul className={s.claims}>
            {model.weather_claims.map((c) => (
              <li key={c.season} className={c.made ? s.yes : s.no}>
                <Icon name={c.made ? 'check' : 'close'} size={16} strokeWidth={2.4} />
                {t.science.seasons[c.season]}: {c.made ? t.science.claimMade : t.science.claimNotMade}
              </li>
            ))}
          </ul>
        </Reveal>

        <Reveal className={s.gates}>
          <h3 className="h2">{t.science.gatesTitle}</h3>
          <div className={s.tableWrap} tabIndex={0} role="region" aria-label={t.science.tableCaption}>
            <table className={s.table}>
              <thead><tr><th scope="col">{t.science.gateCol}</th><th scope="col">{t.science.seasonCol}</th><th scope="col">{t.science.resultCol}</th><th scope="col">{t.science.detailCol}</th></tr></thead>
              <tbody>
                {gates.map((g) => (
                  <tr key={`${g.gate}-${g.season}`}>
                    <th scope="row"><span className="mono">{g.gate}</span> · {t.science.gateNames[g.gate]}</th>
                    <td>{t.science.seasons[g.season]}</td>
                    <td>{g.passed ? <span className={s.yes}>{t.science.passed}</span> : <span className={s.no}>{t.science.failed}</span>}</td>
                    <td className={s.detail}>{pick(g.detail)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <p className="mono muted small">{t.science.freeze(model.freeze_commit.slice(0, 7))}</p>
        </Reveal>

        <div className={s.notes}>
          <Reveal className={s.chartCard}>
            <h3 className="h3">{t.science.reportsTitle}</h3>
            <ul className={s.reports}>
              {model.reports.map((r) => <li key={r.title.en}><strong>{pick(r.title)}</strong><span>{pick(r.text)}</span></li>)}
            </ul>
          </Reveal>
          <Reveal className={s.chartCard}>
            <h3 className="h3">{t.science.limitsTitle}</h3>
            <ul className={s.reports}>{t.science.limits.map((l) => <li key={l}><span>{l}</span></li>)}</ul>
          </Reveal>
        </div>
      </div>
    </section>
  );
}

export function SciencePage() {
  const [params, setParams] = useSearchParams();
  const fromUrl = Number(params.get('nam'));
  const year = YEARS.includes(fromUrl) ? fromUrl : 2010;
  // The year lives in the URL: shareable, survives reload, and the copilot and evidence links can carry it.
  const setYear = useCallback((y: number) => setParams((p) => { const n = new URLSearchParams(p); n.set('nam', String(y)); return n; }, { replace: true, preventScrollReset: true }), [setParams]);
  return (
    <main id="main">
      <GridSection year={year} setYear={setYear} />
      <ClimateSection year={year} setYear={setYear} />
      <ClimateMlSection year={year} setYear={setYear} />
      <RiceSection />
      <SkillSection />
    </main>
  );
}
