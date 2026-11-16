import { lazy, Suspense, useCallback, useEffect, useState, useRef } from 'react';
import { usePageReveals } from '../../motion/cinema';
import { ART } from '../../data/art';
import { PhotoHead } from '../../design-system/PhotoHead';
import { Link, useSearchParams } from 'react-router-dom';
import { geo, hazards, model, YEARS, type RiceSeason, type RuleCode } from '../../data';
import { cellMagnitude, cellMet, magnitudeDigits, RULES, yearShare } from '../../domain/hazards';
import { Icon } from '../../design-system/Icon';
import { Reveal } from '../../design-system/Reveal';
// three.js arrives in its own chunk after the page's text and numbers are on screen
const Observatory3D = lazy(() => import('./Observatory3D').then((m) => ({ default: m.Observatory3D })));
import { YearBars } from '../charts/YearBars';
import { RiceHistoryChart } from '../charts/RiceHistoryChart';
import { SourceValue } from '../provenance/SourceValue';
import { useRefs } from '../provenance/useRefs';
import { useFormat, usePick, useSettings, useT } from '../../app/settings';
import { RainStrip } from '../charts/RainStrip';
import { TwoSources } from '../charts/TwoSources';
import { NdviChart } from '../charts/NdviChart';
import { useLocalTo } from '../../app/paths';
import { useCellName } from '../../hooks/useCellName';
import s from './science.module.css';

const SCIENCE_RULES: RuleCode[] = ['drought_rain_any2', 'drought_rain_consecutive', 'heat', 'heavy_rain', 'cold'];

function GridSection({ year, setYear }: { year: number; setYear: (y: number) => void }) {
  const t = useT();
  const pick = usePick();
  const f = useFormat();
  const refs = useRefs();
  const cellName = useCellName();
  const { calm, lang } = useSettings();
  const [rule, setRule] = useState<RuleCode>('drought_rain_any2');
  const [cell, setCell] = useState<string>(hazards.cells.reduce((a, b) => (b.weight > a.weight ? b : a)).id);
  const [playing, setPlaying] = useState(false);

  useEffect(() => {
    if (!playing) return;
    const id = window.setInterval(
      () => setYear(year >= (YEARS[YEARS.length - 1] as number) ? (YEARS[0] as number) : year + 1),
      1100,
    );
    return () => window.clearInterval(id);
  }, [playing, year, setYear]);

  const share = yearShare(rule, year);
  const info = RULES[rule];
  const sel = geo.grid.find((c) => c.id === cell);

  return (
    <section className={`band surface-forest grain ${s.gridBand}`} aria-labelledby="grid-title">
      <div className="container stack" style={{ ['--gap' as string]: 'var(--s-6)' }}>
        <div className={s.rules} role="radiogroup" aria-label={t.science.rule}>
          {SCIENCE_RULES.map((r) => (
            <button
              key={r}
              type="button"
              role="radio"
              aria-checked={rule === r}
              className={s.ruleBtn}
              onClick={() => setRule(r)}
            >
              <i style={{ background: RULES[r].color }} aria-hidden="true" />
              {pick(RULES[r].name)}
              <span className={s.article}>{pick(RULES[r].article)}</span>
            </button>
          ))}
        </div>

        <p className={s.panelLead}>{t.science.mapLead}</p>
        <div className={s.observatory}>
          <div className={s.stageCol}>
            <h2 id="grid-title" className="visually-hidden">
              {t.science.mapTitle}
            </h2>
            <Suspense
              fallback={
                <div className={s.stagePlaceholder} role="status">
                  {t.common.loading}
                </div>
              }
            >
              <Observatory3D rule={rule} year={year} selected={cell} onSelect={setCell} />
            </Suspense>
          </div>

          <aside className={s.side} aria-label={t.science.readingFor(year)}>
            <div className={s.kpi}>
              <p className={s.kpiLabel}>
                {pick(info.name)} · {pick(info.article)} · <span className="num">{year}</span>
              </p>
              <SourceValue size="xl" {...refs.share(rule, year, share)} />
              <p className={s.kpiSub}>{t.science.shareOfFarmland}</p>
              <p className={s.quote}>“{info.quote}”</p>
              <p className={s.computed}>{pick(info.computed)}</p>
              <p className={s.notForecast}>{t.common.notForecast}</p>
            </div>
            {sel && (
              <dl className={s.cellCard}>
                <dt>{t.science.cell}</dt>
                <dd className="mono">{cellName(sel.id)}</dd>
                <dt>{t.science.weight}</dt>
                <dd className="mono">{f.pct(sel.weight, 1)}</dd>
                <dt>{t.science.measured}</dt>
                <dd className="mono">
                  {f.n(cellMagnitude(info.magnitude, sel.id, year), magnitudeDigits(info.magnitude))} {info.unit[lang]}
                </dd>
                <dt>{t.science.ruleMet}</dt>
                <dd>{cellMet(rule, sel.id, year) ? t.science.met : t.science.notMet}</dd>
              </dl>
            )}
          </aside>
        </div>

        <div className={s.timelineCard}>
          <div className={s.timelineHead}>
            <p className={s.timelineTitle}>
              {pick(info.name)} · {t.science.shareOfFarmland}, {YEARS[0]}–{YEARS[YEARS.length - 1]}
            </p>
            <label className={s.yearSelect}>
              <span>{t.science.year}</span>
              <select
                value={year}
                onChange={(e) => {
                  setPlaying(false);
                  setYear(Number(e.target.value));
                }}
              >
                {YEARS.map((y) => (
                  <option key={y} value={y}>
                    {y}
                  </option>
                ))}
              </select>
            </label>
          </div>
          <div className={s.timeline}>
            <button
              type="button"
              className={s.play}
              onClick={() => setPlaying((p) => !p)}
              aria-pressed={playing}
              disabled={calm && !playing}
              aria-label={playing ? t.science.pause : t.science.play}
            >
              <Icon name={playing ? 'pause' : 'play'} size={18} />
            </button>
            <div className={s.bars}>
              <YearBars
                years={YEARS}
                values={hazards.year_level[rule]}
                color={info.color}
                selected={year}
                onSelect={(y) => {
                  setPlaying(false);
                  setYear(y);
                }}
                height={150}
                label={`${pick(info.name)} · ${t.science.shareOfFarmland}`}
              />
            </div>
          </div>
          <SourceValue {...refs.shareSeries(rule)} />
        </div>

        <div className={s.tableWrap} tabIndex={0} role="region" aria-label={t.science.tableCaption}>
          <table className={s.table}>
            <caption>
              {t.science.tableCaption} · {pick(info.name)} · {year}
            </caption>
            <thead>
              <tr>
                <th scope="col">{t.science.cell}</th>
                <th scope="col">{t.science.weight}</th>
                <th scope="col">
                  {t.science.measured} ({info.unit[lang]})
                </th>
                <th scope="col">{t.science.ruleMet}</th>
              </tr>
            </thead>
            <tbody>
              {hazards.cells.map((c) => (
                <tr key={c.id} aria-selected={c.id === cell} onClick={() => setCell(c.id)}>
                  <th scope="row" className="mono">
                    {cellName(c.id)}
                  </th>
                  <td className="num">{f.pct(c.weight, 1)}</td>
                  <td className="num">
                    {f.n(cellMagnitude(info.magnitude, c.id, year), magnitudeDigits(info.magnitude))}
                  </td>
                  <td>
                    {cellMet(rule, c.id, year) ? (
                      <span className={s.yes}>{t.science.yes}</span>
                    ) : (
                      <span className={s.no}>{t.science.no}</span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          <p className={s.tableSource}>
            <SourceValue {...refs.cellTable(rule, year)} />
          </p>
        </div>
      </div>
    </section>
  );
}

const CELLS = ['19.0_105.0', '19.0_105.625', '18.5_105.625', '19.5_105.0', '19.5_105.625'];

/** One shared year: the rain strip, the two rain sources and the greenness follow the observatory's year. */
function ClimateSection({ year, setYear }: { year: number; setYear: (y: number) => void }) {
  const t = useT();
  const local = useLocalTo();
  const refs = useRefs();
  const cellName = useCellName();
  const [cell, setCell] = useState(CELLS[0] as string);
  const q = new URLSearchParams({ q: t.climate.askYearQ(year), hoi: '1' }).toString();
  return (
    <section className="band surface-paper" aria-labelledby="climate-title">
      <div className="container stack" style={{ ['--gap' as string]: 'var(--s-8)' }}>
        <Reveal className={s.colHead}>
          <h2 id="climate-title" className="h1">
            {t.climate.sectionTitle} · <span className="num">{year}</span>
          </h2>
          <p className="lead">{t.climate.sectionLead}</p>
          <Link className={s.askLink} to={local(`/tro-ly?${q}`)}>
            <Icon name="spark" size={18} />
            {t.climate.askYear(year)}
          </Link>
        </Reveal>
        <Reveal className={s.chartCard}>
          <RainStrip year={year} onYear={setYear} />
        </Reveal>
        <div className={s.skillGrid}>
          <Reveal className={s.chartCard}>
            <h3 className="h3">{t.climate.twoHead}</h3>
            <p className="muted">{t.climate.twoLead}</p>
            <label className={s.yearSelect}>
              <span>{t.climate.cellLabel}</span>
              <select value={cell} onChange={(e) => setCell(e.target.value)}>
                {CELLS.map((c) => (
                  <option key={c} value={c}>
                    {cellName(c)}
                  </option>
                ))}
              </select>
            </label>
            <TwoSources year={year} cell={cell} />
          </Reveal>
          <Reveal className={s.chartCard}>
            <h3 className="h3">{t.climate.ndviHead}</h3>
            <p className="muted">{t.climate.ndviLead}</p>
            <NdviChart year={year} />
            <SourceValue {...refs.ndviSeries()} />
          </Reveal>
        </div>
      </div>
    </section>
  );
}

export function RiceSection() {
  const t = useT();
  const refs = useRefs();
  const [season, setSeason] = useState<RiceSeason>('winter');
  const status = model.seasons.find((x) => x.season === season)?.model_status;
  return (
    <section className="band surface-paper" aria-labelledby="rice-title">
      <div className={`container ${s.twoCol}`}>
        <Reveal className={s.colHead}>
          <h2 id="rice-title" className="h1">
            {t.science.riceTitle}
          </h2>
          <p className="lead">{t.science.riceLead}</p>
          <div className={s.seg} role="radiogroup" aria-label={t.science.riceTitle}>
            {(['spring', 'summer_autumn', 'winter'] as RiceSeason[]).map((x) => (
              <button key={x} type="button" role="radio" aria-checked={season === x} onClick={() => setSeason(x)}>
                {t.science.seasons[x]}
              </button>
            ))}
          </div>
          {status !== 'shown' && (
            <p className={s.notice}>
              <Icon name="alert" size={18} />
              {status === 'not_shown' ? t.science.modelHidden : t.science.notModeled}
            </p>
          )}
        </Reveal>
        <Reveal className={s.chartCard}>
          <RiceHistoryChart season={season} />
          {season === 'winter' && status === 'shown' && (
            <p className={s.notice}>
              <Icon name="alert" size={18} />
              {t.common.winterFragile}
            </p>
          )}
          <div className="cluster">
            <SourceValue {...refs.riceSeries(season)} />
            {status === 'shown' && <SourceValue {...refs.ricePredictionSeries()} />}
          </div>
        </Reveal>
      </div>
    </section>
  );
}

/** The model results live on the method page, read from our API (D-166), so this page shows no second copy. */
function MethodLink() {
  const t = useT();
  const local = useLocalTo();
  return (
    <section className="band surface-paper" aria-labelledby="skill-title">
      <div className={`container ${s.colHead}`}>
        <h2 id="skill-title" className="h1">
          {t.science.skillTitle}
        </h2>
        <Link to={local('/phuong-phap')} className={s.askLink}>
          <Icon name="arrowRight" size={18} />
          {t.science.toMethod}
        </Link>
      </div>
    </section>
  );
}

function ScienceHead({ year }: { year: number }) {
  const t = useT();
  const local = useLocalTo();
  return (
    <PhotoHead shot={ART.pageHead.science} id="science-title" title={t.science.title} lead={t.science.lead}>
      <Link to={local(`/dai-quan-sat?canh=analysis&nam=${year}`)} className={s.globeLink}>
        <Icon name="globe" size={20} />
        {t.science.globeCta}
        <Icon name="arrowRight" size={18} />
      </Link>
    </PhotoHead>
  );
}

export function SciencePage() {
  const pageRef = useRef<HTMLElement>(null);
  usePageReveals(pageRef);
  const [params, setParams] = useSearchParams();
  const fromUrl = Number(params.get('nam'));
  const year = YEARS.includes(fromUrl) ? fromUrl : 2010;
  // The year lives in the URL: shareable, survives reload, and the copilot and evidence links can carry it.
  const setYear = useCallback(
    (y: number) =>
      setParams(
        (p) => {
          const n = new URLSearchParams(p);
          n.set('nam', String(y));
          return n;
        },
        { replace: true, preventScrollReset: true },
      ),
    [setParams],
  );
  return (
    <main ref={pageRef} id="main">
      <ScienceHead year={year} />
      <GridSection year={year} setYear={setYear} />
      <ClimateSection year={year} setYear={setYear} />
      <RiceSection />
      <MethodLink />
    </main>
  );
}
