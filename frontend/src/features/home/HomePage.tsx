import { useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { geo, hazards, model, YEARS } from '../../data';
import { CLIMATE_YEARS } from '../../data/climate';
import { media } from '../../data/media';
import { RULES } from '../../domain/hazards';
import { PLANS } from '../../domain/plans';
import { ButtonLink } from '../../design-system/Button';
import { useSignInAvailable } from '../account/AccountProvider';
import { Icon } from '../../design-system/Icon';
import { Media } from '../../design-system/Media';
import { Reveal } from '../../design-system/Reveal';
import { YearBars } from '../charts/YearBars';
import { RainStrip } from '../charts/RainStrip';
import { SourceValue } from '../provenance/SourceValue';
import { useRefs } from '../provenance/useRefs';
import { useFormat, usePick, useSettings, useT } from '../../app/settings';
import { useLocalTo } from '../../app/paths';
import s from './HomePage.module.css';

const HERO = 'nam-dan-ql46-rice-plain';
const HERITAGE = ['do-luong-nam-son-road-rice', 'lam-river-hong-linh-view', 'do-luong-lam-son-communal-house'];
const STEP_ART = ['c2-fields', 'b1-horizon', 'a3-rice', 'd2-fields'];
const STEP_LINKS = ['/nong-dan/ruong', '/nong-dan/nam', '/nong-dan/uu-tien', '/nong-dan/phuong-an'];

function Hero() {
  const t = useT();
  const pick = usePick();
  const { calm } = useSettings();
  const [paused, setPaused] = useState(false);
  const signIn = useSignInAvailable();
  return (
    <section className={`${s.hero} surface-forest`} aria-labelledby="hero-title">
      <div className={s.heroMedia}>
        <Media slug={HERO} priority sizes="(max-width: 700px) 320px, 100vw" label="none" drift={!calm && !paused} />
      </div>
      <div className={s.heroScrim} aria-hidden="true" />
      <div className={`container ${s.heroInner}`}>
        <p className="eyebrow">{t.home.eyebrow}</p>
        <h1 id="hero-title" className={`display ${s.heroTitle}`}>
          {t.home.titleA}
          <br />
          <em>{t.home.titleB}</em>
        </h1>
        <p className={s.heroLead}>{t.home.lead}</p>
        <div className={s.ctas}>
          <ButtonLink to="/nong-dan/ruong" size="lg" icon="arrowUpRight">
            {t.home.ctaFarmer}
          </ButtonLink>
          <ButtonLink to="/khoa-hoc" size="lg" variant="secondary" icon="layers">
            {t.home.ctaScience}
          </ButtonLink>
        </div>
        {/* a farmer on a second phone finds the saved answers on the first screen (walkthrough of PR #53) */}
        {signIn && (
          <div className={s.ctas}>
            <ButtonLink to="/da-luu" variant="secondary" icon="book">
              {t.account.savedTitle}
            </ButtonLink>
          </div>
        )}
      </div>
      <div className={s.heroFoot}>
        <p className={s.heroCredit}>
          {pick(media(HERO).caption)} · {pick(media(HERO).credit ?? { vi: '', en: '' })}
        </p>
        {!calm && (
          <button type="button" className={s.motionBtn} onClick={() => setPaused((p) => !p)} aria-pressed={paused}>
            <Icon name={paused ? 'play' : 'pause'} size={16} />
            {paused ? t.media.play : t.media.pause}
          </button>
        )}
      </div>
    </section>
  );
}

function ChapterNav() {
  const t = useT();
  return (
    <nav className={s.chapters} aria-label={t.home.chaptersLabel}>
      <ol className="container">
        {t.home.chapters.map((c, i) => (
          <li key={c}>
            <a
              href={`#ch-${i + 1}`}
              onClick={(e) => {
                e.preventDefault();
                document.getElementById(`ch-${i + 1}`)?.scrollIntoView({ behavior: 'smooth' });
              }}
            >
              <span>{String(i + 1).padStart(2, '0')}</span>
              {c}
            </a>
          </li>
        ))}
      </ol>
    </nav>
  );
}

function Heritage() {
  const t = useT();
  const pick = usePick();
  return (
    <section id="ch-1" className="band surface-paper" aria-labelledby="heritage-title">
      <div className={`container ${s.heritage}`}>
        <Reveal className={s.sectionHead}>
          <p className="eyebrow">{t.home.heritageEyebrow}</p>
          <h2 id="heritage-title" className="h1">
            {t.home.heritageTitle}
          </h2>
          <p className="lead">{t.home.heritageLead}</p>
        </Reveal>
        <div className={s.mosaic}>
          {HERITAGE.map((slug, i) => (
            <Reveal as="figure" key={slug} className={s[`m${i}`]} delay={i * 90}>
              <span className={s.mosaicPhoto}>
                <Media
                  slug={slug}
                  sizes={`(max-width: 480px) 320px, (max-width: 860px) 640px, ${i === 0 ? 640 : 420}px`}
                />
              </span>
              <figcaption>
                <span className={s.place}>{pick(media(slug).geography).split(';')[0]}</span>
                <span>{pick(media(slug).caption)}</span>
              </figcaption>
            </Reveal>
          ))}
        </div>
        <ul className={s.regions}>
          {t.home.regions.map((r, i) => (
            <Reveal as="li" key={r.name} delay={i * 70} className={i === 2 ? s.regionOut : undefined}>
              <span className={s.regionName}>{r.name}</span>
              <span className={s.regionBody}>{r.body}</span>
            </Reveal>
          ))}
        </ul>
      </div>
    </section>
  );
}

export function Problem() {
  const t = useT();
  const refs = useRefs();
  const rice = PLANS.find((p) => p.id === 'cc5')?.crops[0];
  return (
    <section id="ch-2" className={`band surface-forest grain ${s.problemBand}`} aria-labelledby="problem-title">
      <div className={`container ${s.problem}`}>
        <Reveal className={s.problemText}>
          <p className="eyebrow">{t.home.problemEyebrow}</p>
          <h2 id="problem-title" className="h1">
            {t.home.problemTitle}
          </h2>
          <p className={s.studyLand}>
            <small>{t.home.studyLandBy}</small>
          </p>
          <p className="lead">{t.home.problemLead}</p>
        </Reveal>
        {/* one study's money only: the second paper defines profit differently (D-52) */}
        <Reveal className={s.problemSide} delay={100}>
          {rice && (
            <div className={s.stat}>
              <SourceValue size="lg" {...refs.cropProfit(rice)} />
              <span>{t.home.riceSpring}</span>
              <span>{t.farmer.definitionPlain.p02}</span>
            </div>
          )}
          <p className={s.trialNote}>{t.home.trialNote}</p>
        </Reveal>
      </div>
    </section>
  );
}

function Climate() {
  const t = useT();
  return (
    <section id="ch-3" className={`band surface-paper ${s.climateBand}`} aria-labelledby="climate-title">
      <div className="container stack" style={{ ['--gap' as string]: 'var(--s-8)' }}>
        <Reveal className={s.sectionHead}>
          <p className="eyebrow">{t.home.climateEyebrow}</p>
          <h2 id="climate-title" className="h1">
            {t.home.climateTitle}
          </h2>
          <p className="lead">{t.home.climateLead}</p>
        </Reveal>
        <Reveal className={s.card}>
          <RainStrip />
        </Reveal>
      </div>
    </section>
  );
}

function Evidence() {
  const t = useT();
  const pick = usePick();
  const refs = useRefs();
  const rule = 'drought_rain_any2' as const;
  const values = hazards.year_level[rule];
  const dryYears = values.filter((v) => v > 0.5).length;
  return (
    <section id="ch-4" className="band surface-paper" aria-labelledby="evidence-title" style={{ paddingTop: 0 }}>
      <div className={`container ${s.evidence}`}>
        <Reveal className={s.sectionHead}>
          <p className="eyebrow">{t.home.evidenceEyebrow}</p>
          <h2 id="evidence-title" className="h1">
            {t.home.evidenceTitle}
          </h2>
          <p className="lead">{t.home.droughtCaption(dryYears)}</p>
          <ButtonLink to="/bang-chung" variant="secondary" icon="arrowRight">
            {t.home.evidenceCta}
          </ButtonLink>
        </Reveal>
        <Reveal className={s.card} delay={90}>
          <div className={s.chartHead}>
            <h3 className="h3">
              {pick(RULES[rule].name)} · {RULES[rule].article}
            </h3>
            <span className="muted">{t.home.droughtAxis}</span>
          </div>
          <YearBars years={YEARS} values={values} color="var(--data-drought)" label={t.home.evidenceTitle} />
          <SourceValue {...refs.shareSeries(rule)} />
          <p className="muted">{t.common.notForecast}</p>
        </Reveal>
      </div>
    </section>
  );
}

function Steps() {
  const t = useT();
  const local = useLocalTo();
  return (
    <section id="ch-5" className={`band surface-forest grain ${s.stepsBand}`} aria-labelledby="steps-title">
      <div className="container stack" style={{ ['--gap' as string]: 'var(--s-10)' }}>
        <Reveal className={s.sectionHead}>
          <p className="eyebrow">{t.home.stepsEyebrow}</p>
          <h2 id="steps-title" className="h1">
            {t.home.stepsTitle}
          </h2>
        </Reveal>
        <ol className={s.steps}>
          {t.home.steps.map((step, i) => (
            <Reveal as="li" key={step.title} delay={i * 70}>
              <Link to={local(STEP_LINKS[i] ?? '/nong-dan')} className={s.step} viewTransition>
                <span className={s.stepArt}>
                  <Media slug={STEP_ART[i] ?? 'a3-rice'} decorative sizes="(min-width: 1000px) 300px, 90vw" />
                  <span className={s.stepNum}>{String(i + 1).padStart(2, '0')}</span>
                </span>
                <span className={s.stepTitle}>{step.title}</span>
                <span className={s.stepBody}>{step.body}</span>
              </Link>
            </Reveal>
          ))}
        </ol>
      </div>
    </section>
  );
}

/** The signature transition: the river photograph dims and the real province border and NASA grid draw over it. */
function Observatory() {
  const t = useT();
  const pick = usePick();
  const shape = useMemo(() => {
    const [minLon, minLat, maxLon, maxLat] = geo.bounds;
    const k = Math.cos((19.3 * Math.PI) / 180);
    const W = (maxLon - minLon) * k * 100 + 20,
      H = (maxLat - minLat) * 100 + 20;
    const x = (lon: number) => (lon - minLon) * k * 100 + 10;
    const y = (lat: number) => (maxLat - lat) * 100 + 10;
    const outline = geo.outline.map((r) => r.map(([lo, la]) => `${x(lo).toFixed(1)},${y(la).toFixed(1)}`).join(' '));
    const cells = geo.grid.map((c) => ({
      id: c.id,
      w: c.weight,
      x: x(c.lon - 0.3125),
      y: y(c.lat + 0.25),
      cw: 0.625 * k * 100,
      ch: 50,
    }));
    return { W, H, outline, cells };
  }, []);
  return (
    <section id="ch-6" className={`${s.obs} surface-forest`} aria-labelledby="obs-title">
      <Reveal className={s.obsStage}>
        <span className={s.obsPhoto}>
          <Media slug="lam-river-vinh-ben-thuy" sizes="100vw" label="none" decorative />
        </span>
        <svg
          className={s.obsSvg}
          viewBox={`0 0 ${shape.W} ${shape.H}`}
          aria-hidden="true"
          preserveAspectRatio="xMidYMid meet"
        >
          {shape.cells.map((c, i) => (
            <rect
              key={c.id}
              x={c.x}
              y={c.y}
              width={c.cw}
              height={c.ch}
              className={s.drawCell}
              pathLength={1}
              style={{ transitionDelay: `${300 + i * 90}ms`, fillOpacity: c.w > 0 ? 0.08 + c.w * 0.5 : 0 }}
            />
          ))}
          {shape.outline.map((pts, i) => (
            <polygon key={i} points={pts} className={s.drawLine} pathLength={1} />
          ))}
        </svg>
      </Reveal>
      <div className={`container ${s.obsText}`}>
        <p className="eyebrow">{t.home.obsEyebrow}</p>
        <h2 id="obs-title" className="h1">
          {t.home.obsTitle}
        </h2>
        <p className="lead">{t.home.obsLead}</p>
        <dl className={s.obsFacts}>
          <div>
            <dt className="num">{hazards.cells.length}</dt>
            <dd>{t.home.obsCells}</dd>
          </div>
          <div>
            <dt className="num">{CLIMATE_YEARS.length}</dt>
            <dd>{t.home.obsYears}</dd>
          </div>
        </dl>
        <ButtonLink to="/dai-quan-sat" size="lg" icon="globe">
          {t.home.obsCta}
        </ButtonLink>
        <p className={s.obsCredit}>
          {pick(media('lam-river-vinh-ben-thuy').caption)} ·{' '}
          {pick(media('lam-river-vinh-ben-thuy').credit ?? { vi: '', en: '' })}
        </p>
      </div>
    </section>
  );
}

function Honesty() {
  const t = useT();
  const pick = usePick();
  const f = useFormat();
  const status = (season: 'spring' | 'winter') => model.seasons.find((x) => x.season === season)?.model_status;
  const m1 = (season: 'spring' | 'winter') =>
    model.metrics.find(
      (m) =>
        m.model_id === 'm1_ridge' && m.season === season && m.subset === 'national' && m.scheme === 'rolling_origin',
    );
  const g2 = (season: 'spring' | 'winter') => model.gates.find((g) => g.gate === 'G2' && g.season === season);
  const cards: {
    key: 'spring' | 'winter' | 'summer';
    title: string;
    body: string;
    ok: boolean;
    skill: number | undefined;
  }[] = [
    {
      key: 'spring' as const,
      title: t.science.seasons.spring,
      body: t.home.honestySpring,
      ok: status('spring') === 'shown',
      skill: m1('spring')?.skill_vs_bnw?.value,
    },
    {
      key: 'winter' as const,
      title: t.science.seasons.winter,
      body: t.home.honestyWinter,
      ok: status('winter') === 'shown',
      skill: m1('winter')?.skill_vs_bnw?.value,
    },
    {
      key: 'summer' as const,
      title: t.science.seasons.summer_autumn,
      body: t.home.honestySummer,
      ok: false,
      skill: undefined as number | undefined,
    },
  ];
  return (
    <section id="ch-7" className="band surface-paper" aria-labelledby="honesty-title">
      <div className={`container ${s.honesty}`}>
        <Reveal className={s.sectionHead}>
          <p className="eyebrow">{t.home.honestyEyebrow}</p>
          <h2 id="honesty-title" className="h1">
            {t.home.honestyTitle}
          </h2>
          <p className="lead">{t.home.honestyLead}</p>
          <ButtonLink to="/khoa-hoc" variant="secondary" icon="arrowRight">
            {t.home.honestyCta}
          </ButtonLink>
        </Reveal>
        <div className={s.seasonCards}>
          {cards.map((c, i) => (
            <Reveal key={c.key} className={s.seasonCard} delay={i * 80}>
              <span className={[s.verdict, c.ok ? s.verdictOk : s.verdictNo].join(' ')}>
                <Icon name={c.ok ? 'check' : 'close'} size={16} strokeWidth={2.4} />
                {c.ok ? t.science.claimMade : t.science.claimNotMade}
              </span>
              <h3 className="h3">{c.title}</h3>
              <p>{c.body}</p>
              {c.key === 'winter' && (
                <p>
                  <strong>{t.common.winterFragile}</strong>
                </p>
              )}
              {c.skill !== undefined && c.key !== 'summer' && (
                <p className={s.skillLine}>
                  <span className="muted">
                    {t.science.models.m1_ridge} {t.home.vsBnw}
                  </span>
                  <SourceValue
                    sourceId="e012"
                    kind="model"
                    value={f.n(c.skill, 2)}
                    label={`${c.title} · ${t.home.skillVsBnw}`}
                    detail={pick(g2(c.key as 'spring' | 'winter')?.detail ?? { vi: '', en: '' })}
                  />
                </p>
              )}
            </Reveal>
          ))}
        </div>
      </div>
    </section>
  );
}

function Faq() {
  const t = useT();
  return (
    <section className="band surface-paper" aria-labelledby="faq-title" style={{ paddingTop: 0 }}>
      <div className={`container ${s.faqGrid}`}>
        <Reveal className={s.sectionHead}>
          <p className="eyebrow">{t.home.faqEyebrow}</p>
          <h2 id="faq-title" className="h1">
            {t.home.faqTitle}
          </h2>
          <p className="muted">{t.common.support}</p>
        </Reveal>
        <Reveal className={s.faq}>
          {t.home.faq.map((item, i) => (
            <details key={item.q} open={i === 0}>
              <summary>
                {item.q}
                <span className={s.faqIcon} aria-hidden="true">
                  <Icon name="chevronDown" size={18} />
                </span>
              </summary>
              <p>{item.a}</p>
            </details>
          ))}
        </Reveal>
      </div>
    </section>
  );
}

function Invite() {
  const t = useT();
  return (
    <section id="ch-8" className={`${s.invite} surface-forest`} aria-labelledby="invite-title">
      <span className={s.inviteArt}>
        <Media slug="d1-horizon" sizes="100vw" />
      </span>
      <div className={`container ${s.inviteInner}`}>
        <h2 id="invite-title" className={`display ${s.inviteTitle}`}>
          {t.home.inviteTitle}
        </h2>
        <p className="lead">{t.home.inviteLead}</p>
        <div className={s.ctas}>
          <ButtonLink to="/nong-dan/ruong" size="lg" icon="arrowUpRight">
            {t.home.ctaFarmer}
          </ButtonLink>
          <ButtonLink to="/tro-ly" size="lg" variant="secondary" icon="spark">
            {t.home.ctaCopilot}
          </ButtonLink>
        </div>
      </div>
    </section>
  );
}

export function HomePage() {
  return (
    <main id="main">
      <Hero />
      <ChapterNav />
      <Heritage />
      <Problem />
      <Climate />
      <Evidence />
      <Steps />
      <Observatory />
      <Honesty />
      <Faq />
      <Invite />
    </main>
  );
}
