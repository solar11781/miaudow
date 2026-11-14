import { useMemo } from 'react';
import { Link } from 'react-router-dom';
import { hazards, model, YEARS } from '../../data';
import { PHOTOS, type PhotoSlug } from '../../data/photos';
import { RULES, yearShare } from '../../domain/hazards';
import { PLANS } from '../../domain/plans';
import { ButtonLink } from '../../design-system/Button';
import { Icon, type IconName } from '../../design-system/Icon';
import { Photo } from '../../design-system/Photo';
import { Reveal } from '../../design-system/Reveal';
import { YearBars } from '../charts/YearBars';
import { SourceValue } from '../provenance/SourceValue';
import { useRefs } from '../provenance/useRefs';
import { useFormat, usePick, useT } from '../../app/settings';
import s from './HomePage.module.css';

const STEP_PHOTOS: PhotoSlug[] = ['canh-dong-tren-cao', 'dap-lua', 'phoi-tuong', 'dam-sen'];
const STEP_LINKS = ['/nong-dan/ruong', '/nong-dan/nam', '/nong-dan/uu-tien', '/nong-dan/phuong-an'];
const GALLERY: PhotoSlug[] = ['doi-che', 'bac-thang-nang', 'bac-thang-song', 'bac-thang-gat', 'bac-thang-duong', 'phoi-tuong'];
const SOURCES_STRIP: [IconName, string][] = [['satellite', 'NASA POWER'], ['grid', 'NASA MODIS'], ['scale', 'QĐ 18/2021'], ['drop', 'TCVN 8641'], ['leaf', 'P-02 · VAAS'], ['chart', 'Cục Thống kê']];

function Hero() {
  const t = useT();
  const f = useFormat();
  const pick = usePick();
  const refs = useRefs();
  const year = YEARS[YEARS.length - 1] as number;
  const rule = 'drought_rain_any2' as const;
  const share = yearShare(rule, year);
  return (
    <section className={`${s.hero} surface-forest grain`} aria-labelledby="hero-title">
      <div className={s.glow} aria-hidden="true" />
      <div className={`container ${s.heroGrid}`}>
        <div className={s.heroText}>
          <p className="eyebrow">{t.home.eyebrow}</p>
          <h1 id="hero-title" className={`display ${s.heroTitle}`}>
            {t.home.titleA} <em>{t.home.titleB}</em>
          </h1>
          <p className={`lead ${s.heroLead}`}>{t.home.lead}</p>
          <div className={s.ctas}>
            <ButtonLink to="/nong-dan/ruong" size="lg" icon="arrowUpRight">{t.home.ctaFarmer}</ButtonLink>
            <ButtonLink to="/khoa-hoc" size="lg" variant="secondary" icon="layers">{t.home.ctaScience}</ButtonLink>
          </div>
          <dl className={s.facts} aria-label={t.home.factsLabel}>
            <div><dt className="num">{hazards.cells.length}</dt><dd>{t.home.factCells}</dd></div>
            <div><dt className="num">{YEARS.length}</dt><dd>{t.home.factYears}</dd></div>
            <div><dt className="num">{PLANS.length}</dt><dd>{t.home.factPlans}</dd></div>
          </dl>
        </div>
        <div className={s.heroArt}>
          <div className={s.mainPhoto}>
            <Photo slug="ganh-ma" priority sizes="(min-width: 1000px) 520px, 90vw" className={s.kenburns} />
            <span className={s.photoTag}>{pick(PHOTOS['ganh-ma'].caption)} · {t.home.photoNote}</span>
          </div>
          <div className={s.sidePhoto} aria-hidden="true">
            <Photo slug="dap-lua" decorative sizes="220px" />
          </div>
          <div className={s.dataCard}>
            <p className={s.dataLabel}>{pick(RULES[rule].name)} · {RULES[rule].article}</p>
            <SourceValue size="xl" {...refs.share(rule, year, share)} />
            <p className={s.dataSub}>{t.common.farmland} Nghệ An · {year}</p>
            <div className={s.miniBars} aria-hidden="true">
              {hazards.year_level[rule].map((v, i) => (
                <i key={YEARS[i]} style={{ height: `${Math.max(6, v * 100)}%`, opacity: i === YEARS.length - 1 ? 1 : 0.45 }} />
              ))}
            </div>
            <p className={s.dataFoot}>{YEARS[0]} → {year} · NASA POWER × {f.n(hazards.cells.length)}</p>
          </div>
        </div>
      </div>
    </section>
  );
}

function SourcesStrip() {
  const t = useT();
  return (
    <section className={`${s.strip} surface-forest`} aria-label={t.home.sourcesLabel}>
      <ul className="container">
        {SOURCES_STRIP.map(([icon, name]) => <li key={name}><Icon name={icon} size={20} />{name}</li>)}
      </ul>
    </section>
  );
}

function Problem() {
  const t = useT();
  const f = useFormat();
  const pick = usePick();
  const refs = useRefs();
  const rule = 'drought_rain_any2' as const;
  const values = hazards.year_level[rule];
  const dryYears = values.filter((v) => v > 0.5).length;
  const cc5 = PLANS.find((p) => p.id === 'cc5');
  const rice = cc5?.crops[0];
  return (
    <section className="band surface-paper" aria-labelledby="problem-title">
      <div className={`container ${s.problem}`}>
        <Reveal className={s.problemText}>
          <p className="eyebrow">{t.home.problemEyebrow}</p>
          <h2 id="problem-title" className="h1">{t.home.problemTitle}</h2>
          <p className="lead">{t.home.problemLead}</p>
          <figure className={s.quote}>
            <blockquote>{t.home.quote}</blockquote>
            <figcaption>{t.home.quoteBy}</figcaption>
          </figure>
          <div className={s.stats}>
            {rice && (
              <div className={s.stat}>
                <SourceValue size="lg" {...refs.cropProfit(rice)} />
                <span>{t.home.riceSpring}</span>
              </div>
            )}
            <div className={s.stat}>
              <SourceValue size="lg" sourceId="p03" kind="study" value={`${f.n(1.16, 2)} ${t.common.millionPerHa}`} label={t.home.riceSummer} />
              <span>{t.home.riceSummer}</span>
            </div>
          </div>
        </Reveal>
        <Reveal className={s.problemPhoto} delay={80}>
          <Photo slug="la-sen-non-la" sizes="(min-width: 1000px) 480px, 90vw" />
          <span className={s.caption}>{pick(PHOTOS['la-sen-non-la'].caption)}</span>
        </Reveal>
        <Reveal className={s.chartCard} delay={120}>
          <div className={s.chartHead}>
            <h3 className="h3">{t.home.droughtTitle}</h3>
            <span className={s.chartRule}>{RULES[rule].article} · {pick(RULES[rule].name)}</span>
          </div>
          <YearBars years={YEARS} values={values} color="var(--data-drought)" label={t.home.droughtTitle} />
          <p className={s.chartCaption}>
            {t.home.droughtCaption(dryYears)}{' '}
            <Link to="/khoa-hoc" viewTransition className={s.inlineLink}>{t.home.ctaScience}</Link>
          </p>
        </Reveal>
      </div>
    </section>
  );
}

function Steps() {
  const t = useT();
  return (
    <section className={`band surface-forest grain ${s.stepsBand}`} aria-labelledby="steps-title">
      <div className="container stack" style={{ ['--gap' as string]: 'var(--s-10)' }}>
        <Reveal className={s.sectionHead}>
          <p className="eyebrow">{t.home.stepsEyebrow}</p>
          <h2 id="steps-title" className="h1">{t.home.stepsTitle}</h2>
        </Reveal>
        <ol className={s.steps}>
          {t.home.steps.map((step, i) => (
            <Reveal as="li" key={step.title} delay={i * 70}>
              <Link to={STEP_LINKS[i] ?? '/nong-dan'} className={s.step} viewTransition>
                <span className={s.stepPhoto}>
                  <Photo slug={STEP_PHOTOS[i] ?? 'dam-sen'} decorative sizes="(min-width: 1000px) 300px, 90vw" />
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

function Honesty() {
  const t = useT();
  const pick = usePick();
  const f = useFormat();
  const g2 = (season: 'spring' | 'winter') => model.gates.find((g) => g.gate === 'G2' && g.season === season);
  const status = useMemo(() => ({
    spring: model.seasons.find((x) => x.season === 'spring')?.model_status,
    winter: model.seasons.find((x) => x.season === 'winter')?.model_status,
  }), []);
  const m1 = (season: 'spring' | 'winter') => model.metrics.find((m) => m.model_id === 'm1_ridge' && m.season === season && m.subset === 'national' && m.scheme === 'rolling_origin');
  const cards: { key: string; title: string; body: string; ok: boolean; skill?: number }[] = [
    { key: 'spring', title: t.science.seasons.spring, body: t.home.honestySpring, ok: status.spring === 'shown', skill: m1('spring')?.skill_vs_bnw?.value },
    { key: 'winter', title: t.science.seasons.winter, body: t.home.honestyWinter, ok: status.winter === 'shown', skill: m1('winter')?.skill_vs_bnw?.value },
    { key: 'summer', title: t.science.seasons.summer_autumn, body: t.home.honestySummer, ok: false },
  ];
  return (
    <section className="band surface-paper" aria-labelledby="honesty-title">
      <div className={`container ${s.honesty}`}>
        <Reveal className={s.sectionHead}>
          <p className="eyebrow">{t.home.honestyEyebrow}</p>
          <h2 id="honesty-title" className="h1">{t.home.honestyTitle}</h2>
          <p className="lead">{t.home.honestyLead}</p>
          <ButtonLink to="/khoa-hoc" variant="secondary" icon="arrowRight">{t.home.honestyCta}</ButtonLink>
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
              {c.skill !== undefined && (
                <p className={s.skillLine}>
                  <span className="muted small">{t.science.models.m1_ridge} vs BNW</span>
                  <SourceValue sourceId="e012" kind="model" value={f.n(c.skill, 3)} label={`${c.title} · skill vs BNW`}
                    detail={pick(g2(c.key as 'spring' | 'winter')?.detail ?? { vi: '', en: '' })} />
                </p>
              )}
            </Reveal>
          ))}
        </div>
      </div>
    </section>
  );
}

function Heritage() {
  const t = useT();
  const pick = usePick();
  const region = (r: string) => (r === 'lowland' ? t.home.regionLowland : r === 'midland' ? t.home.regionMidland : t.home.regionMountain);
  return (
    <section className="band surface-forest grain" aria-labelledby="heritage-title">
      <div className="container stack" style={{ ['--gap' as string]: 'var(--s-8)' }}>
        <Reveal className={s.heritageHead}>
          <div>
            <p className="eyebrow">{t.home.heritageEyebrow}</p>
            <h2 id="heritage-title" className="h1">{t.home.heritageTitle}</h2>
          </div>
          <p className="lead">{t.home.heritageLead}</p>
        </Reveal>
      </div>
      <div className={s.gallery} role="region" aria-label={t.home.heritageTitle} tabIndex={0}>
        {GALLERY.map((slug) => (
          <figure key={slug} className={s.gItem}>
            <span className={s.gPhoto}><Photo slug={slug} sizes="(min-width: 900px) 380px, 78vw" /></span>
            <figcaption>
              <span className={s.gRegion} data-region={PHOTOS[slug].region}>{region(PHOTOS[slug].region)}</span>
              <span>{pick(PHOTOS[slug].caption)}</span>
            </figcaption>
          </figure>
        ))}
      </div>
    </section>
  );
}

function Faq() {
  const t = useT();
  return (
    <section className="band surface-paper" aria-labelledby="faq-title">
      <div className={`container ${s.faqGrid}`}>
        <Reveal className={s.sectionHead}>
          <p className="eyebrow">{t.home.faqEyebrow}</p>
          <h2 id="faq-title" className="h1">{t.home.faqTitle}</h2>
          <p className="muted">{t.common.support}</p>
        </Reveal>
        <Reveal className={s.faq}>
          {t.home.faq.map((item, i) => (
            <details key={item.q} open={i === 0}>
              <summary>{item.q}<span className={s.faqIcon} aria-hidden="true"><Icon name="arrowUpRight" size={18} /></span></summary>
              <p>{item.a}</p>
            </details>
          ))}
        </Reveal>
      </div>
    </section>
  );
}

export function HomePage() {
  return (
    <main id="main">
      <Hero />
      <SourcesStrip />
      <Problem />
      <Steps />
      <Honesty />
      <Heritage />
      <Faq />
    </main>
  );
}
