import { useEffect, useRef, useState } from 'react';
import { Brocade } from '../../design-system/Brocade';
import { Accent } from '../../design-system/Accent';
import { SatelliteScan } from '../cinema/SatelliteScan';
import { usePageReveals } from '../../motion/cinema';
import { Link, useLocation } from 'react-router-dom';
import { hazards, model, YEARS } from '../../data';
import { ART } from '../../data/art';
import { RULES } from '../../domain/hazards';
import { PLANS } from '../../domain/plans';
import { ButtonLink } from '../../design-system/Button';
import { Icon, type IconName } from '../../design-system/Icon';
import { Media } from '../../design-system/Media';
import { EASE, gsap, riseLines, useCinema } from '../../motion/cinema';
import { YearBars } from '../charts/YearBars';
import { SourceValue } from '../provenance/SourceValue';
import { useRefs } from '../provenance/useRefs';
import { useFormat, usePick, useSettings, useT } from '../../app/settings';
import { useSignInAvailable } from '../account/AccountProvider';
import { useLocalTo } from '../../app/paths';
import s from './HomePage.module.css';

const STEP_LINKS = ['/nong-dan/ruong', '/nong-dan/nam', '/nong-dan/uu-tien', '/nong-dan/phuong-an'];
const SLIDE_MS = 7000;

/** Opening: photographs that change by themselves (pausable, H1), the title rising out of its mask. */
function Hero() {
  const t = useT();
  const signIn = useSignInAvailable();
  const { calm } = useSettings();
  const root = useRef<HTMLElement>(null);
  const [shown, setShown] = useState(0);
  const [paused, setPaused] = useState(false);
  const [later, setLater] = useState(false);
  const slides = later ? ART.hero : ART.hero.slice(0, 1);
  const playing = !calm && !paused;

  useEffect(() => {
    const id = window.setTimeout(() => setLater(true), 2500);
    return () => window.clearTimeout(id);
  }, []);

  useEffect(() => {
    if (!playing || slides.length < 2) return;
    const id = window.setInterval(() => setShown((n) => (n + 1) % slides.length), SLIDE_MS);
    return () => window.clearInterval(id);
  }, [playing, slides.length]);

  useCinema(root, () => {
    const title = root.current?.querySelector('[data-rise]');
    if (title) riseLines(title, 0.45);
    gsap.from('[data-letterbox]', { scaleY: 1, duration: 1.7, ease: EASE.calm, delay: 0.15 });
    gsap.from('[data-hero-stage]', { scale: 1.16, duration: 2.8, ease: EASE.heavy });
    gsap.to('[data-hero-stage]', {
      yPercent: 14,
      ease: 'none',
      scrollTrigger: { trigger: root.current, start: 'top top', end: 'bottom top', scrub: true },
    });
    gsap.from('[data-hero-after]', { opacity: 0, y: 16, duration: 1.1, ease: EASE.heavy, delay: 0.85, stagger: 0.1 });
  }, [t.home.titleA]);

  return (
    <section ref={root} className={`${s.hero} surface-forest`} aria-labelledby="hero-title">
      <div className={s.heroStage} data-hero-stage>
        {slides.map((shot, n) => (
          <div key={shot.slug} className={[s.slide, n === shown ? s.slideOn : ''].join(' ')}>
            <Media
              slug={shot.slug}
              narrow={shot.narrow}
              priority={n === 0}
              sizes="(max-width: 480px) 320px, 100vw"
              decorative
              drift={playing && n === shown}
            />
          </div>
        ))}
      </div>
      <div className={s.heroScrim} aria-hidden="true" />
      <span className={`${s.letterbox} ${s.letterTop}`} data-letterbox aria-hidden="true" />
      <span className={`${s.letterbox} ${s.letterBottom}`} data-letterbox aria-hidden="true" />
      <div className={`container ${s.heroInner}`}>
        <h1 key={t.home.titleA} id="hero-title" className={`display ${s.heroTitle}`} data-rise>
          {t.home.titleA}
          <br />
          <em>{t.home.titleB}</em>
        </h1>
        <p className={s.heroLead} data-hero-after>
          {t.home.lead}
        </p>
        <div className={s.ctas} data-hero-after>
          <ButtonLink to="/nong-dan/ruong" size="lg" icon="arrowRight">
            {t.home.ctaFarmer}
          </ButtonLink>
          <a
            className={s.textLink}
            href="#cores"
            onClick={(e) => {
              e.preventDefault();
              document.getElementById('cores')?.scrollIntoView({ behavior: calm ? 'auto' : 'smooth' });
            }}
          >
            {t.home.ctaCores}
            <Icon name="chevronDown" size={18} />
          </a>
        </div>
        {/* a farmer on a second phone finds the saved answers on the first screen (walkthrough of PR #53) */}
        {signIn && (
          <div className={s.ctas} data-hero-after>
            <ButtonLink to="/da-luu" size="lg" variant="secondary" icon="book">
              {t.account.savedTitle}
            </ButtonLink>
          </div>
        )}
      </div>
      <div className={`container ${s.heroFoot}`} data-hero-after>
        <ol className={s.progress} aria-hidden="true">
          {slides.map((shot, n) => (
            <li
              key={shot.slug}
              className={n === shown ? s.progressOn : ''}
              style={{ animationDuration: `${SLIDE_MS}ms`, animationPlayState: playing ? 'running' : 'paused' }}
            />
          ))}
        </ol>
        {!calm && (
          <button type="button" className={s.motionBtn} onClick={() => setPaused((p) => !p)}>
            <Icon name={paused ? 'play' : 'pause'} size={16} />
            {paused ? t.home.play : t.home.pause}
          </button>
        )}
      </div>
    </section>
  );
}

/** The trial land in the paper's own words, one photograph, one study's money with its own definition (D-52, D-160). */
export function Problem() {
  const t = useT();
  const f = useFormat();
  const refs = useRefs();
  const root = useRef<HTMLElement>(null);
  const rice = PLANS.find((p) => p.id === 'cc5')?.crops[0];

  useCinema(root, () => {
    gsap.fromTo(
      '[data-clip]',
      { clipPath: 'inset(14% 10% 14% 10%)' },
      {
        clipPath: 'inset(0% 0% 0% 0%)',
        ease: 'none',
        scrollTrigger: { trigger: root.current, start: 'top 85%', end: 'center 55%', scrub: true },
      },
    );
  });

  return (
    <section ref={root} id="ch-2" className={`${s.problem} surface-forest grain`} aria-labelledby="problem-title">
      <div className={s.problemPhoto} data-clip>
        <Media
          slug={ART.problem.slug}
          narrow={ART.problem.narrow}
          sizes="(max-width: 480px) 320px, (min-width: 900px) 50vw, 100vw"
        />
      </div>
      <div className={s.problemText}>
        <h2 id="problem-title" className="h1">
          {t.home.problemTitle}
        </h2>
        <p className="lead">{t.home.problemLead}</p>
        {/* one study's money only: the second paper defines profit differently (D-52) */}
        {rice && (
          <div className={s.money}>
            <SourceValue size="xl" {...refs.cropProfit(rice)}>
              {f.million(rice.profit)}
              <span className={s.unit}>{t.common.millionPerHa}</span>
            </SourceValue>
            <span className={s.moneyLabel}>{t.home.riceSpring}</span>
            <span className={s.moneyDefinition}>{t.farmer.definitionPlain.p02}</span>
          </div>
        )}
        <p className={s.note}>{t.home.trialNote}</p>
      </div>
    </section>
  );
}

/** The folk verse of xứ Nghệ, in brush lettering between two brocade bands, over the winding road. */
function Verse() {
  const t = useT();
  const root = useRef<HTMLElement>(null);
  useCinema(root, () => {
    const st = { trigger: root.current, start: 'top 72%', once: true };
    root.current?.querySelectorAll('[data-verse-line]').forEach((line, i) => {
      gsap.from(line, {
        clipPath: 'inset(0% 100% 0% 0%)',
        duration: 1.6,
        ease: EASE.calm,
        delay: 0.3 + i * 0.55,
        scrollTrigger: st,
        clearProps: 'clipPath',
      });
    });
    gsap.from('[data-brocade]', { scaleX: 0, duration: 1.4, ease: EASE.heavy, stagger: 0.2, scrollTrigger: st });
    gsap.fromTo(
      '[data-verse-photo]',
      { yPercent: -10 },
      {
        yPercent: 10,
        ease: 'none',
        scrollTrigger: { trigger: root.current, start: 'top bottom', end: 'bottom top', scrub: true },
      },
    );
  });
  return (
    <section ref={root} className={`${s.verse} surface-forest`} aria-labelledby="verse-title">
      <div className={s.versePhoto} data-verse-photo>
        <Media slug={ART.verse.slug} narrow={ART.verse.narrow} sizes="(max-width: 480px) 320px, 100vw" decorative />
      </div>
      <div className={`container ${s.verseInner}`}>
        <h2 id="verse-title" className="visually-hidden">
          {t.home.verseTitle}
        </h2>
        <Brocade className={s.verseBand} data-brocade />
        <blockquote className={s.verseText} lang="vi">
          {t.home.verse.map((line) => (
            <span key={line} className={s.verseLine} data-verse-line>
              {line}
            </span>
          ))}
        </blockquote>
        <p className={s.verseBy}>{t.home.verseBy}</p>
        <p className={s.verseNote}>{t.home.verseNote}</p>
        <Brocade className={s.verseBand} data-brocade />
      </div>
    </section>
  );
}

/** The four AI cores: the photograph holds while each core's text passes (sticky, so it works without motion too). */
const CORE_ICONS: IconName[] = ['sun', 'book', 'sprout', 'mic'];

function Cores() {
  const t = useT();
  const local = useLocalTo();
  const { calm } = useSettings();
  const root = useRef<HTMLElement>(null);
  const [active, setActive] = useState(0);
  const cores = t.home.cores;

  useEffect(() => {
    const items = root.current?.querySelectorAll<HTMLElement>('[data-core]');
    if (!items?.length || !('IntersectionObserver' in window)) return;
    const io = new IntersectionObserver(
      (entries) =>
        entries.forEach((e) => {
          if (e.isIntersecting) setActive(Number((e.target as HTMLElement).dataset.core));
        }),
      { rootMargin: '-45% 0px -45% 0px' },
    );
    items.forEach((el) => io.observe(el));
    return () => io.disconnect();
  }, []);

  useCinema(root, ({ wide }) => {
    if (!wide) return;
    gsap.fromTo(
      '[data-core-stage]',
      { scale: 1.08 },
      {
        scale: 1,
        ease: 'none',
        scrollTrigger: { trigger: root.current, start: 'top bottom', end: 'bottom top', scrub: true },
      },
    );
  });

  return (
    <section ref={root} id="cores" className={`${s.cores} surface-forest`} aria-labelledby="cores-title">
      <div className={`container ${s.coresHead}`}>
        <div className={s.coresIntro}>
          <h2 id="cores-title" className="h1">
            <Accent text={t.home.coresTitle} />
          </h2>
          <p className="lead">{t.home.coresLead}</p>
        </div>
        <ol className={s.coreIndex}>
          {cores.map((c, n) => (
            <li key={c.name} className={n === active ? s.coreIndexOn : undefined}>
              <a
                href={`#core-${n}`}
                onClick={(e) => {
                  e.preventDefault();
                  document
                    .getElementById(`core-${n}`)
                    ?.closest('article')
                    ?.scrollIntoView({ behavior: calm ? 'auto' : 'smooth', block: 'center' });
                }}
              >
                <span className={s.coreIcon}>
                  <Icon name={CORE_ICONS[n] ?? 'spark'} size={24} />
                </span>
                <span className={s.coreIndexText}>
                  <strong>{c.name}</strong>
                  <span>{c.gives}</span>
                </span>
              </a>
            </li>
          ))}
        </ol>
      </div>
      <Brocade className={s.coresBand} />
      <div className={s.coresBody}>
        <div className={s.coresStage} aria-hidden="true">
          <div className={s.coresStageInner} data-core-stage>
            {ART.cores.map((shot, n) => (
              <div key={shot.slug} className={[s.coreShot, n === active ? s.coreShotOn : ''].join(' ')}>
                <Media slug={shot.slug} sizes="(max-width: 480px) 320px, 50vw" decorative />
              </div>
            ))}
          </div>
          <p className={s.coreStageName}>{cores[active]?.name}</p>
          <ol className={s.coreTicks}>
            {cores.map((c, n) => (
              <li key={c.name} className={n === active ? s.coreTickOn : undefined} />
            ))}
          </ol>
        </div>
        <div className={s.coreList}>
          {cores.map((c, n) => (
            <article key={c.name} className={s.core} data-core={n} aria-labelledby={`core-${n}`}>
              <span className={s.corePhoto}>
                <Media slug={(ART.cores[n] ?? ART.cores[0]).slug} sizes="(max-width: 480px) 320px, 100vw" decorative />
              </span>
              <h3 id={`core-${n}`} className={s.coreName}>
                {c.name}
              </h3>
              <p className={s.coreDoes}>{c.does}</p>
              <dl className={s.coreFacts}>
                <div>
                  <dt>{t.home.coreUses}</dt>
                  <dd>{c.uses}</dd>
                </div>
                <div>
                  <dt>{t.home.coreGives}</dt>
                  <dd>{c.gives}</dd>
                </div>
                <div className={s.coreLimit}>
                  <dt>{t.home.coreLimit}</dt>
                  <dd>{c.limit}</dd>
                </div>
              </dl>
              <Link to={local(c.to)} className={s.coreLink}>
                {t.home.coreOpen(c.where)}
                <Icon name="arrowRight" size={18} />
              </Link>
            </article>
          ))}
        </div>
      </div>
    </section>
  );
}

/** Thirty years in one plain sentence and one bar per year. */
function Climate() {
  const t = useT();
  const pick = usePick();
  const refs = useRefs();
  const rule = 'drought_rain_any2' as const;
  const values = hazards.year_level[rule];
  const dryYears = values.filter((v) => v > 0.5).length;
  return (
    <section className={`band surface-paper ${s.climate}`} aria-labelledby="climate-title">
      <div className={`container ${s.climateGrid}`}>
        <div className={s.climateText}>
          <h2 id="climate-title" className="h1">
            {t.home.climateTitle(dryYears)}
          </h2>
          <p className="lead">{t.home.climateLead}</p>
          <ButtonLink to="/bang-chung" variant="secondary" icon="arrowRight">
            {t.home.evidenceCta}
          </ButtonLink>
        </div>
        <figure className={s.chart}>
          <figcaption className={s.chartHead}>
            <span className={s.chartRule}>
              {pick(RULES[rule].name)} · {RULES[rule].article}
            </span>
            <span className="muted">{t.home.droughtAxis}</span>
          </figcaption>
          <YearBars years={YEARS} values={values} color="var(--data-drought)" label={t.home.climateTitle(dryYears)} />
          <SourceValue {...refs.shareSeries(rule)} />
          <p className="muted">{t.common.notForecast}</p>
        </figure>
      </div>
    </section>
  );
}

/** What the models could and could not show, as the method page reports it (D-165 wording kept). */
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
      key: 'spring',
      title: t.science.seasons.spring,
      body: t.home.honestySpring,
      ok: status('spring') === 'shown',
      skill: m1('spring')?.skill_vs_bnw?.value,
    },
    {
      key: 'winter',
      title: t.science.seasons.winter,
      body: t.home.honestyWinter,
      ok: status('winter') === 'shown',
      skill: m1('winter')?.skill_vs_bnw?.value,
    },
    { key: 'summer', title: t.science.seasons.summer_autumn, body: t.home.honestySummer, ok: false, skill: undefined },
  ];
  return (
    <section className={`band surface-paper ${s.honesty}`} aria-labelledby="honesty-title">
      <div className={`container ${s.honestyGrid}`}>
        <div className={s.honestyHead}>
          <h2 id="honesty-title" className="h1">
            {t.home.honestyTitle}
          </h2>
          <p className="lead">{t.home.honestyLead}</p>
          <ButtonLink to="/khoa-hoc" variant="secondary" icon="arrowRight">
            {t.home.honestyCta}
          </ButtonLink>
        </div>
        <div className={s.seasonCards} data-stagger>
          {cards.map((c) => (
            <article key={c.key} className={s.seasonCard}>
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
              {c.skill !== undefined && (
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
            </article>
          ))}
        </div>
      </div>
    </section>
  );
}

function Steps() {
  const t = useT();
  const local = useLocalTo();
  return (
    <section className={`band surface-forest grain ${s.steps}`} aria-labelledby="steps-title">
      <div className="container stack" style={{ ['--gap' as string]: 'var(--s-10)' }}>
        <h2 id="steps-title" className="h1">
          <Accent text={t.home.stepsTitle} />
        </h2>
        <ol className={s.strip} data-stagger>
          {t.home.steps.map((step, i) => (
            <li key={step.title}>
              <Link to={local(STEP_LINKS[i] ?? '/nong-dan')} className={s.step}>
                <span className={s.stepPhoto}>
                  <Media
                    slug={ART.steps[i]?.slug ?? ART.steps[0].slug}
                    decorative
                    sizes="(max-width: 480px) 320px, (min-width: 1000px) 320px, 80vw"
                  />
                </span>
                <span className={s.stepText}>
                  <span className={s.stepLabel}>{t.home.stepLabel(i + 1)}</span>
                  <span className={s.stepTitle}>{step.title}</span>
                  <span className={s.stepBody}>{step.body}</span>
                </span>
              </Link>
            </li>
          ))}
        </ol>
      </div>
    </section>
  );
}

/** The two satellites scanning the real province and its NASA grid (drawn, light, pausable), then the way in. */
function Observatory() {
  const t = useT();
  return (
    <section className={`${s.obs} surface-forest`} aria-labelledby="obs-title">
      <div className={s.obsStage}>
        <SatelliteScan labels={t.earth.scan} />
      </div>
      <div className={`container ${s.obsText}`}>
        <h2 id="obs-title" className="h1">
          <Accent text={t.home.obsTitle} />
        </h2>
        <p className="lead">{t.home.obsLead}</p>
        <ButtonLink to="/dai-quan-sat" size="lg" icon="arrowRight">
          {t.home.obsCta}
        </ButtonLink>
      </div>
    </section>
  );
}

function Invite() {
  const t = useT();
  const root = useRef<HTMLElement>(null);
  useCinema(root, () => {
    gsap.fromTo(
      '[data-invite-art]',
      { scale: 1.18 },
      {
        scale: 1,
        ease: 'none',
        scrollTrigger: { trigger: root.current, start: 'top bottom', end: 'bottom bottom', scrub: true },
      },
    );
  });
  return (
    <section ref={root} className={`${s.invite} surface-forest`} aria-labelledby="invite-title">
      <span className={s.inviteArt} data-invite-art>
        <Media slug={ART.invite.slug} sizes="(max-width: 480px) 320px, 100vw" decorative />
      </span>
      <div className={`container ${s.inviteInner}`}>
        <h2 id="invite-title" className={`display ${s.inviteTitle}`}>
          <Accent text={t.home.inviteTitle} />
        </h2>
        <p className="lead">{t.home.inviteLead}</p>
        <div className={s.ctas}>
          <ButtonLink to="/nong-dan/ruong" size="lg" icon="arrowRight">
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
  const pageRef = useRef<HTMLElement>(null);
  usePageReveals(pageRef);
  const { state } = useLocation();
  const { calm } = useSettings();
  // A core tag elsewhere links here with { to: 'cores' }: land on the four cores once the page has laid out.
  useEffect(() => {
    if ((state as { to?: string } | null)?.to !== 'cores') return;
    const id = window.requestAnimationFrame(() =>
      document.getElementById('cores')?.scrollIntoView({ behavior: calm ? 'auto' : 'smooth' }),
    );
    return () => window.cancelAnimationFrame(id);
  }, [state, calm]);
  return (
    <main ref={pageRef} id="main">
      <Hero />
      <Problem />
      <Verse />
      <Cores />
      <Climate />
      <Honesty />
      <Steps />
      <Observatory />
      <Invite />
    </main>
  );
}
