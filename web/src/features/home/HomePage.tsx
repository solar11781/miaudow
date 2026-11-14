import { useEffect, useMemo, useRef, useState } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { geo, hazards, YEARS } from '../../data';
import { ART } from '../../data/art';
import { RULES } from '../../domain/hazards';
import { PLANS } from '../../domain/plans';
import { ButtonLink } from '../../design-system/Button';
import { Icon } from '../../design-system/Icon';
import { Media } from '../../design-system/Media';
import { EASE, gsap, riseLines, useCinema } from '../../motion/cinema';
import { YearBars } from '../charts/YearBars';
import { SourceValue } from '../provenance/SourceValue';
import { useRefs } from '../provenance/useRefs';
import { useFormat, usePick, useSettings, useT } from '../../app/settings';
import s from './HomePage.module.css';

const STEP_LINKS = ['/nong-dan/ruong', '/nong-dan/nam', '/nong-dan/uu-tien', '/nong-dan/phuong-an'];
const SLIDE_MS = 7000;

/** Opening: photographs that change by themselves (pausable, H1), the title rising out of its mask. */
function Hero() {
  const t = useT();
  const { calm } = useSettings();
  const root = useRef<HTMLElement>(null);
  const [shown, setShown] = useState(0);
  const [paused, setPaused] = useState(false);
  const slides = ART.hero;
  const playing = !calm && !paused;

  useEffect(() => {
    if (!playing) return;
    const id = window.setInterval(() => setShown((n) => (n + 1) % slides.length), SLIDE_MS);
    return () => window.clearInterval(id);
  }, [playing, slides.length]);

  useCinema(root, () => {
    const title = root.current?.querySelector('[data-rise]');
    if (title) riseLines(title, 0.2);
    gsap.from('[data-hero-stage]', { scale: 1.14, duration: 2.6, ease: EASE.heavy });
    gsap.from('[data-hero-after]', { autoAlpha: 0, y: 16, duration: 1.1, ease: EASE.heavy, delay: 0.85, stagger: 0.1 });
  }, [t.home.titleA]);

  return (
    <section ref={root} className={`${s.hero} surface-forest`} aria-labelledby="hero-title">
      <div className={s.heroStage} data-hero-stage>
        {slides.map((shot, n) => (
          <div key={shot.slug} className={[s.slide, n === shown ? s.slideOn : ''].join(' ')}>
            <Media slug={shot.slug} narrow={shot.narrow} priority sizes="100vw" decorative drift={playing && n === shown} />
          </div>
        ))}
      </div>
      <div className={s.heroScrim} aria-hidden="true" />
      <div className={`container ${s.heroInner}`}>
        <h1 key={t.home.titleA} id="hero-title" className={`display ${s.heroTitle}`} data-rise>
          {t.home.titleA}<br /><em>{t.home.titleB}</em>
        </h1>
        <p className={s.heroLead} data-hero-after>{t.home.lead}</p>
        <div className={s.ctas} data-hero-after>
          <ButtonLink to="/nong-dan/ruong" size="lg" icon="arrowRight">{t.home.ctaFarmer}</ButtonLink>
          <a className={s.textLink} href="#cores" onClick={(e) => { e.preventDefault(); document.getElementById('cores')?.scrollIntoView({ behavior: calm ? 'auto' : 'smooth' }); }}>
            {t.home.ctaCores}<Icon name="chevronDown" size={18} />
          </a>
        </div>
      </div>
      <div className={`container ${s.heroFoot}`} data-hero-after>
        <ol className={s.progress} aria-hidden="true">
          {slides.map((shot, n) => <li key={shot.slug} className={n === shown ? s.progressOn : ''} style={{ animationDuration: `${SLIDE_MS}ms`, animationPlayState: playing ? 'running' : 'paused' }} />)}
        </ol>
        {!calm && (
          <button type="button" className={s.motionBtn} onClick={() => setPaused((p) => !p)} aria-pressed={paused}>
            <Icon name={paused ? 'play' : 'pause'} size={16} />{paused ? t.home.play : t.home.pause}
          </button>
        )}
      </div>
    </section>
  );
}

/** One statement, one photograph, two sourced numbers. */
function Problem() {
  const t = useT();
  const f = useFormat();
  const refs = useRefs();
  const root = useRef<HTMLElement>(null);
  const rice = PLANS.find((p) => p.id === 'cc5')?.crops[0];

  useCinema(root, () => {
    gsap.fromTo('[data-clip]', { clipPath: 'inset(14% 10% 14% 10%)' }, {
      clipPath: 'inset(0% 0% 0% 0%)', ease: 'none',
      scrollTrigger: { trigger: root.current, start: 'top 85%', end: 'center 55%', scrub: true },
    });
  });

  return (
    <section ref={root} className={`${s.problem} surface-forest grain`} aria-labelledby="problem-title">
      <div className={s.problemPhoto} data-clip>
        <Media slug={ART.problem.slug} narrow={ART.problem.narrow} sizes="(min-width: 900px) 50vw, 100vw" />
      </div>
      <div className={s.problemText}>
        <h2 id="problem-title" className="h1">{t.home.problemTitle}</h2>
        <p className="lead">{t.home.problemLead}</p>
        <div className={s.pair}>
          {rice && (
            <div className={s.pairItem}>
              <SourceValue size="xl" {...refs.cropProfit(rice)}>{f.million(rice.profit)}<span className={s.unit}>{t.common.millionPerHa}</span></SourceValue>
              <span>{t.home.riceSpring}</span>
            </div>
          )}
          <div className={s.pairItem}>
            <SourceValue size="xl" sourceId="p03" kind="study" value={`${f.n(1.16, 2)} ${t.common.millionPerHa}`} label={t.home.riceSummer}
              detail={t.home.riceSummerDetail}>{f.n(1.16, 2)}<span className={s.unit}>{t.common.millionPerHa}</span></SourceValue>
            <span>{t.home.riceSummer}</span>
          </div>
        </div>
        <p className={s.note}>{t.home.trialNote}</p>
      </div>
    </section>
  );
}

/** The four AI cores: the photograph holds while each core's text passes (sticky, so it works without motion too). */
function Cores() {
  const t = useT();
  const root = useRef<HTMLElement>(null);
  const [active, setActive] = useState(0);
  const cores = t.home.cores;

  useEffect(() => {
    const items = root.current?.querySelectorAll<HTMLElement>('[data-core]');
    if (!items?.length || !('IntersectionObserver' in window)) return;
    const io = new IntersectionObserver(
      (entries) => entries.forEach((e) => { if (e.isIntersecting) setActive(Number((e.target as HTMLElement).dataset.core)); }),
      { rootMargin: '-45% 0px -45% 0px' },
    );
    items.forEach((el) => io.observe(el));
    return () => io.disconnect();
  }, []);

  useCinema(root, ({ wide }) => {
    if (!wide) return;
    gsap.fromTo('[data-core-stage]', { scale: 1.08 }, {
      scale: 1, ease: 'none',
      scrollTrigger: { trigger: root.current, start: 'top bottom', end: 'bottom top', scrub: true },
    });
  });

  return (
    <section ref={root} id="cores" className={`${s.cores} surface-forest`} aria-labelledby="cores-title">
      <div className={`container ${s.coresHead}`}>
        <h2 id="cores-title" className="h1">{t.home.coresTitle}</h2>
        <p className="lead">{t.home.coresLead}</p>
      </div>
      <div className={s.coresBody}>
        <div className={s.coresStage} aria-hidden="true">
          <div className={s.coresStageInner} data-core-stage>
            {ART.cores.map((shot, n) => (
              <div key={shot.slug} className={[s.coreShot, n === active ? s.coreShotOn : ''].join(' ')}>
                <Media slug={shot.slug} sizes="50vw" decorative />
              </div>
            ))}
          </div>
          <p className={s.coreStageName}>{cores[active]?.name}</p>
          <ol className={s.coreTicks}>{cores.map((c, n) => <li key={c.name} className={n === active ? s.coreTickOn : undefined} />)}</ol>
        </div>
        <div className={s.coreList}>
          {cores.map((c, n) => (
            <article key={c.name} className={s.core} data-core={n} aria-labelledby={`core-${n}`}>
              <span className={s.corePhoto}><Media slug={(ART.cores[n] ?? ART.cores[0]).slug} sizes="100vw" decorative /></span>
              <h3 id={`core-${n}`} className={s.coreName}>{c.name}</h3>
              <p className={s.coreDoes}>{c.does}</p>
              <dl className={s.coreFacts}>
                <div><dt>{t.home.coreUses}</dt><dd>{c.uses}</dd></div>
                <div><dt>{t.home.coreGives}</dt><dd>{c.gives}</dd></div>
                <div className={s.coreLimit}><dt>{t.home.coreLimit}</dt><dd>{c.limit}</dd></div>
              </dl>
              <Link to={c.to} className={s.coreLink} viewTransition>{t.home.coreOpen(c.where)}<Icon name="arrowRight" size={18} /></Link>
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
  const rule = 'drought_rain_any2' as const;
  const values = hazards.year_level[rule];
  const dryYears = values.filter((v) => v > 0.5).length;
  return (
    <section className={`band surface-paper ${s.climate}`} aria-labelledby="climate-title">
      <div className={`container ${s.climateGrid}`}>
        <div className={s.climateText}>
          <h2 id="climate-title" className="h1">{t.home.climateTitle(dryYears)}</h2>
          <p className="lead">{t.home.climateLead}</p>
          <ButtonLink to="/bang-chung" variant="secondary" icon="arrowRight">{t.home.evidenceCta}</ButtonLink>
        </div>
        <figure className={s.chart}>
          <figcaption className={s.chartHead}>
            <span className={s.chartRule}>{pick(RULES[rule].name)} · {RULES[rule].article}</span>
            <span className="muted">{t.home.droughtAxis}</span>
          </figcaption>
          <YearBars years={YEARS} values={values} color="var(--data-drought)" label={t.home.climateTitle(dryYears)} />
          <p className="muted">{t.common.notForecast}</p>
        </figure>
      </div>
    </section>
  );
}

function Steps() {
  const t = useT();
  return (
    <section className={`band surface-forest grain ${s.steps}`} aria-labelledby="steps-title">
      <div className="container stack" style={{ ['--gap' as string]: 'var(--s-10)' }}>
        <h2 id="steps-title" className="h1">{t.home.stepsTitle}</h2>
        <ol className={s.strip}>
          {t.home.steps.map((step, i) => (
            <li key={step.title}>
              <Link to={STEP_LINKS[i] ?? '/nong-dan'} className={s.step} viewTransition>
                <span className={s.stepPhoto}><Media slug={ART.steps[i]?.slug ?? ART.steps[0].slug} decorative sizes="(min-width: 1000px) 320px, 80vw" /></span>
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

/** The photograph dims and the real province border and NASA grid draw over it. */
function Observatory() {
  const t = useT();
  const root = useRef<HTMLElement>(null);
  const shape = useMemo(() => {
    const [minLon, minLat, maxLon, maxLat] = geo.bounds;
    const k = Math.cos((19.3 * Math.PI) / 180);
    const W = (maxLon - minLon) * k * 100 + 20, H = (maxLat - minLat) * 100 + 20;
    const x = (lon: number) => (lon - minLon) * k * 100 + 10;
    const y = (lat: number) => (maxLat - lat) * 100 + 10;
    const outline = geo.outline.map((r) => r.map(([lo, la]) => `${x(lo).toFixed(1)},${y(la).toFixed(1)}`).join(' '));
    const cells = geo.grid.map((c) => ({ id: c.id, w: c.weight, x: x(c.lon - 0.3125), y: y(c.lat + 0.25), cw: 0.625 * k * 100, ch: 50 }));
    return { W, H, outline, cells };
  }, []);

  useCinema(root, () => {
    const st = { trigger: root.current, start: 'top 70%' };
    gsap.from('[data-draw-line]', { strokeDashoffset: 1, duration: 2.4, ease: EASE.calm, scrollTrigger: st });
    gsap.from('[data-draw-cell]', { strokeDashoffset: 1, fillOpacity: 0, duration: 1.2, ease: EASE.calm, stagger: 0.12, delay: 0.6, scrollTrigger: st });
  });

  return (
    <section ref={root} className={`${s.obs} surface-forest`} aria-labelledby="obs-title">
      <div className={s.obsStage}>
        <span className={s.obsPhoto}><Media slug={ART.observatory.slug} sizes="100vw" decorative /></span>
        <svg className={s.obsSvg} viewBox={`0 0 ${shape.W} ${shape.H}`} aria-hidden="true" preserveAspectRatio="xMidYMid meet">
          {shape.cells.map((c) => (
            <rect key={c.id} x={c.x} y={c.y} width={c.cw} height={c.ch} className={s.drawCell} pathLength={1} data-draw-cell
              style={{ fillOpacity: c.w > 0 ? 0.08 + c.w * 0.5 : 0 }} />
          ))}
          {shape.outline.map((pts, i) => <polygon key={i} points={pts} className={s.drawLine} pathLength={1} data-draw-line />)}
        </svg>
      </div>
      <div className={`container ${s.obsText}`}>
        <h2 id="obs-title" className="h1">{t.home.obsTitle}</h2>
        <p className="lead">{t.home.obsLead}</p>
        <ButtonLink to="/dai-quan-sat" size="lg" icon="arrowRight">{t.home.obsCta}</ButtonLink>
      </div>
    </section>
  );
}

function Invite() {
  const t = useT();
  return (
    <section className={`${s.invite} surface-forest`} aria-labelledby="invite-title">
      <span className={s.inviteArt}><Media slug={ART.invite.slug} sizes="100vw" decorative /></span>
      <div className={`container ${s.inviteInner}`}>
        <h2 id="invite-title" className={`display ${s.inviteTitle}`}>{t.home.inviteTitle}</h2>
        <p className="lead">{t.home.inviteLead}</p>
        <div className={s.ctas}>
          <ButtonLink to="/nong-dan/ruong" size="lg" icon="arrowRight">{t.home.ctaFarmer}</ButtonLink>
          <ButtonLink to="/tro-ly" size="lg" variant="secondary" icon="spark">{t.home.ctaCopilot}</ButtonLink>
        </div>
      </div>
    </section>
  );
}

export function HomePage() {
  const { state } = useLocation();
  const { calm } = useSettings();
  // A core tag elsewhere links here with { to: 'cores' }: land on the four cores once the page has laid out.
  useEffect(() => {
    if ((state as { to?: string } | null)?.to !== 'cores') return;
    const id = window.requestAnimationFrame(() => document.getElementById('cores')?.scrollIntoView({ behavior: calm ? 'auto' : 'smooth' }));
    return () => window.cancelAnimationFrame(id);
  }, [state, calm]);
  return (
    <main id="main">
      <Hero />
      <Problem />
      <Cores />
      <Climate />
      <Steps />
      <Observatory />
      <Invite />
    </main>
  );
}
