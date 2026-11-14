import { useCallback, useEffect, useMemo, useRef, useState, type RefObject } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import eyesJson from '@data/nasa_eyes.json';
import { geo } from '../../data';
import { Icon } from '../../design-system/Icon';
import { SourceValue } from '../provenance/SourceValue';
import { useFormat, usePick, useSettings, useT } from '../../app/settings';
import { MISSIONS, type Mission } from './missions';
import { isScene, SCENES, type Scene, type SceneId } from './scenes';
import type { Globe, Overlay } from './globe';
import { cellYear } from './cellClimate';
import s from './earth.module.css';

const EYES = eyesJson as unknown as { links: { id: string; url: string }[] };
const eyesUrl = (id: string) => EYES.links.find((l) => l.id === id)?.url;
const CELLS = geo.grid.filter((c) => c.weight > 0).map((c) => c.id);
const OVERLAYS: Overlay[] = ['none', 's2', 'ndvi-modis', 'imerg', 'smap'];
const YEARS = Array.from({ length: 34 }, (_, i) => 1991 + i);
const PLANETS = ['moon', 'mars', 'jupiter', 'saturn'] as const;
const COMPOSITE_IDS = ['summer_autumn-2020', 'autumn_winter-2020', 'spring-2021', 'spring-2024', 'summer_autumn-2024', 'autumn_winter-2024'] as const;
const AUTOPLAY_MS = 9000;

type Eyes = { id: string; name: string };
type OpenEyes = (id: string, name: string) => void;

function hasWebGL(): boolean {
  try {
    const c = document.createElement('canvas');
    return !!(c.getContext('webgl2') ?? c.getContext('webgl'));
  } catch {
    return false;
  }
}

/** One page, one shared state in the URL: scene, year, overlay, composite and the selected cell. */
function useObservatoryState() {
  const [params, setParams] = useSearchParams();
  const scene: SceneId = isScene(params.get('canh')) ? (params.get('canh') as SceneId) : 'cosmos';
  const y = Number(params.get('nam'));
  const year = YEARS.includes(y) ? y : 2020;
  const overlay = (OVERLAYS as string[]).includes(params.get('lop') ?? '') ? (params.get('lop') as Overlay) : 's2';
  const composite = (COMPOSITE_IDS as readonly string[]).includes(params.get('mua') ?? '') ? (params.get('mua') as string) : COMPOSITE_IDS[0];
  const cell = CELLS.includes(params.get('o') ?? '') ? (params.get('o') as string) : (CELLS[2] ?? '19.0_105.0');
  const set = useCallback((patch: Record<string, string>) => setParams((p) => {
    const n = new URLSearchParams(p);
    for (const [k, v] of Object.entries(patch)) n.set(k, v);
    return n;
  }, { replace: true, preventScrollReset: true }), [setParams]);
  return { scene, year, overlay, composite, cell, set };
}
type ObservatoryState = ReturnType<typeof useObservatoryState>;

const showsLayers = (sc: Scene) => sc.panel === 'layers' || sc.panel === 'metric' || sc.panel === 'insight';

/** The CesiumJS globe: its own chunk, loaded only here, disposed on leave, kept in step with the URL state. */
function useGlobe(on: boolean, st: ObservatoryState, sceneDef: Scene, onFail: () => void) {
  const { calm, lang } = useSettings();
  const host = useRef<HTMLDivElement>(null);
  const credits = useRef<HTMLDivElement>(null);
  const globe = useRef<Globe | null>(null);
  const [ready, setReady] = useState(false);
  const pickRef = useRef((id: string) => st.set({ o: id }));
  useEffect(() => { pickRef.current = (id: string) => st.set({ o: id }); }, [st]);

  useEffect(() => {
    if (!on || !host.current || !credits.current) return;
    let disposed = false;
    const el = host.current, creditEl = credits.current;
    // CesiumJS reads its workers and sky textures from here (copied by pipeline/copy_cesium.mjs)
    (window as unknown as { CESIUM_BASE_URL?: string }).CESIUM_BASE_URL = new URL('cesium/', document.baseURI).href;
    import('./globe')
      .then(({ createGlobe }) => {
        if (disposed) return;
        globe.current = createGlobe(el, creditEl, (id) => pickRef.current(id), lang);
        setReady(true);
      })
      .catch(onFail);
    return () => { disposed = true; globe.current?.dispose(); globe.current = null; setReady(false); };
  }, [on, lang, onFail]);

  const firstMove = useRef(true);
  useEffect(() => {
    if (!ready || !globe.current) return;
    globe.current.goTo(sceneDef.id, firstMove.current || calm);
    globe.current.setOrbits(sceneDef.orbits, !calm);
    firstMove.current = false;
  }, [ready, sceneDef, calm]);
  useEffect(() => { if (ready) globe.current?.setYear(st.year); }, [ready, st.year]);
  useEffect(() => { if (ready) globe.current?.setSelected(st.cell); }, [ready, st.cell]);
  useEffect(() => {
    if (ready) globe.current?.setOverlay(showsLayers(sceneDef) ? st.overlay : 'none', st.year, st.composite);
  }, [ready, sceneDef, st.overlay, st.year, st.composite]);

  return { host, credits, stop: () => globe.current?.stopFlight() };
}

export function EarthPage() {
  const t = useT();
  const { calm } = useSettings();
  const st = useObservatoryState();
  const supported = useMemo(() => typeof window !== 'undefined' && hasWebGL(), []);
  const [globeOk, setGlobeOk] = useState(true);
  const onFail = useCallback(() => setGlobeOk(false), []);
  const live3d = supported && !calm && globeOk;
  const idx = Math.max(0, SCENES.findIndex((x) => x.id === st.scene));
  const sceneDef = SCENES[idx] as Scene;
  const { host, credits, stop } = useGlobe(live3d, st, sceneDef, onFail);
  const [autoplay, setAutoplay] = useState(false);
  const [eyes, setEyes] = useState<Eyes | null>(null);
  const eyesDialog = useRef<HTMLDialogElement>(null);

  // autoplay through the scenes: starts only on request, pausable, never under reduced motion
  useEffect(() => {
    if (!autoplay || calm) return;
    const id = window.setTimeout(() => {
      const next = SCENES[idx + 1];
      if (next) st.set({ canh: next.id }); else setAutoplay(false);
    }, AUTOPLAY_MS);
    return () => window.clearTimeout(id);
  }, [autoplay, calm, idx, st]);

  const go = (id: SceneId) => { setAutoplay(false); st.set({ canh: id }); };
  const openEyes: OpenEyes = (id, name) => { setEyes({ id, name }); requestAnimationFrame(() => eyesDialog.current?.showModal()); };
  const closeEyes = (backToNgheAn: boolean) => {
    eyesDialog.current?.close();
    setEyes(null);
    if (backToNgheAn) go('nghe-an');
  };

  return (
    <main id="main" className={`${s.page} surface-forest`}>
      <section className={s.stage} aria-labelledby="earth-title">
        {live3d ? (
          <div ref={host} className={s.globe} role="img" aria-label={t.earth.globeLabel} onPointerDown={() => { setAutoplay(false); stop(); }} />
        ) : (
          <div className={s.fallback}>
            <p>{calm ? t.earth.calmNote : t.earth.noWebgl}</p>
            <Link to={`/khoa-hoc?nam=${st.year}`} className={s.fallbackLink}>{t.earth.openScience}<Icon name="arrowRight" size={18} /></Link>
          </div>
        )}
        <div ref={credits} className={s.credits} />

        <header className={s.head}>
          <p className="eyebrow">{t.earth.eyebrow}</p>
          <h1 id="earth-title" className={s.title}>{t.earth.title}</h1>
          <p className={s.sceneName}><span className={s.sceneNum}>{String(idx + 1).padStart(2, '0')}/{String(SCENES.length).padStart(2, '0')}</span>{t.earth.scenes[st.scene].title}</p>
        </header>

        <ScenePanel st={st} sceneDef={sceneDef} openEyes={openEyes} />
        <SceneRail idx={idx} go={go} autoplay={autoplay} onAutoplay={() => setAutoplay((a) => !a)} />
      </section>

      <EyesDialog dialog={eyesDialog} eyes={eyes} onClose={closeEyes} onDismiss={() => setEyes(null)} />
    </main>
  );
}

function ScenePanel({ st, sceneDef, openEyes }: { st: ObservatoryState; sceneDef: Scene; openEyes: OpenEyes }) {
  const t = useT();
  const insight = sceneDef.panel === 'insight';
  return (
    <aside className={s.panel} aria-label={t.earth.scenes[st.scene].title}>
      <p className={s.panelLead}>{t.earth.scenes[st.scene].body}</p>
      {st.scene === 'cosmos' && (
        <div className={s.planets}>
          <p className={s.small}>{t.earth.planetsLead}</p>
          <div className={s.chips}>
            {PLANETS.map((p) => <button key={p} type="button" onClick={() => openEyes(p, t.earth.planets[p])}>{t.earth.planets[p]}</button>)}
          </div>
        </div>
      )}
      {sceneDef.panel === 'missions' && (
        <div className={s.missions}>
          <p className={s.illustrative}><Icon name="alert" size={18} />{t.earth.orbitNote}</p>
          {MISSIONS.map((m) => <MissionCard key={m.id} m={m} onEyes={openEyes} />)}
        </div>
      )}
      {showsLayers(sceneDef) && <LayerControls st={st} overlays={!insight} />}
      {(sceneDef.panel === 'metric' || insight) && <CellMetric cell={st.cell} year={st.year} onCell={(c) => st.set({ o: c })} insight={insight} />}
      {(st.scene === 'earth' || st.scene === 'vietnam') && <p className={s.small}>{t.earth.gibsCredit}</p>}
    </aside>
  );
}

function MissionCard({ m, onEyes }: { m: Mission; onEyes: OpenEyes }) {
  const t = useT();
  const pick = usePick();
  const eyes = m.eyesId ? eyesUrl(m.eyesId) : undefined;
  return (
    <article className={s.mission} style={{ ['--m' as string]: m.color }}>
      <header className={s.missionHead}>
        <span className={s.missionDot} aria-hidden="true" />
        <h3>{m.name}</h3>
        <span className={s.status} data-status={m.status}>{t.earth.status[m.status]}</span>
      </header>
      <p className={s.agency}>{m.agency} · {m.altitudeKm} km · {m.inclinationDeg}°</p>
      <dl className={s.facts}>
        <dt>{t.earth.observes}</dt><dd>{pick(m.observes)}</dd>
        <dt>{t.earth.product}</dt><dd>{pick(m.product)}</dd>
        <dt>{t.earth.resolution}</dt><dd>{pick(m.resolution)} · {pick(m.coverage)}</dd>
        <dt>{t.earth.forFarming}</dt><dd>{pick(m.why)}</dd>
      </dl>
      <p className={s.statusNote}>{pick(m.statusNote)}</p>
      <div className={s.missionLinks}>
        {m.eyesId && eyes && (
          <button type="button" className={s.eyesBtn} onClick={() => onEyes(m.eyesId as string, m.name)}><Icon name="satellite" size={18} />{t.earth.openEyes}</button>
        )}
        <a href={m.source} target="_blank" rel="noreferrer" className={s.srcLink}>{t.earth.missionPage}<Icon name="arrowUpRight" size={16} /></a>
      </div>
    </article>
  );
}

function LayerControls({ st, overlays }: { st: ObservatoryState; overlays: boolean }) {
  const t = useT();
  return (
    <div className={s.controls}>
      <label className={s.field}>
        <span>{t.earth.year}</span>
        <select value={st.year} onChange={(e) => st.set({ nam: e.target.value })}>
          {YEARS.map((y) => <option key={y} value={y}>{y}</option>)}
        </select>
      </label>
      {overlays && <OverlayPicker st={st} />}
    </div>
  );
}

function OverlayPicker({ st }: { st: ObservatoryState }) {
  const t = useT();
  return (
    <>
      <fieldset className={s.overlays}>
        <legend>{t.earth.overlayLabel}</legend>
        {OVERLAYS.map((o) => (
          <label key={o} className={s.radio}>
            <input type="radio" name="overlay" value={o} checked={st.overlay === o} onChange={() => st.set({ lop: o })} />
            <span>{t.earth.overlays[o].name}</span>
            {o !== 'none' && <span className={s.kind} data-kind={o === 's2' ? 'data' : 'visual'}>{o === 's2' ? t.earth.kindData : t.earth.kindVisual}</span>}
          </label>
        ))}
      </fieldset>
      {st.overlay === 's2' && (
        <label className={s.field}>
          <span>{t.earth.season}</span>
          <select value={st.composite} onChange={(e) => st.set({ mua: e.target.value })}>
            {COMPOSITE_IDS.map((c) => <option key={c} value={c}>{t.earth.composites[c]}</option>)}
          </select>
        </label>
      )}
      {st.overlay !== 'none' && <p className={s.small}>{t.earth.overlays[st.overlay].note(st.year)}</p>}
    </>
  );
}

function SceneRail({ idx, go, autoplay, onAutoplay }: { idx: number; go: (id: SceneId) => void; autoplay: boolean; onAutoplay: () => void }) {
  const t = useT();
  const { calm } = useSettings();
  const prev = SCENES[idx - 1];
  const next = SCENES[idx + 1];
  const list = useRef<HTMLOListElement>(null);
  // keep the current scene in view on narrow screens (scrolls the rail only, never the page)
  useEffect(() => {
    const ol = list.current;
    const b = ol?.querySelector('[aria-current="step"]')?.getBoundingClientRect();
    if (!ol || !b) return;
    const o = ol.getBoundingClientRect();
    ol.scrollBy({ left: b.left + b.width / 2 - (o.left + o.width / 2), behavior: calm ? 'auto' : 'smooth' });
  }, [idx, calm]);
  return (
    <nav className={s.rail} aria-label={t.earth.railLabel}>
      <button type="button" className={s.railStep} onClick={() => prev && go(prev.id)} disabled={!prev} aria-label={t.earth.prev}>
        <Icon name="arrowLeft" size={20} />
      </button>
      <ol ref={list} className={s.scenes}>
        {SCENES.map((x, i) => (
          <li key={x.id}>
            <button type="button" aria-current={i === idx ? 'step' : undefined} onClick={() => go(x.id)}>
              <span className={s.n}>{String(i + 1).padStart(2, '0')}</span>
              <span className={s.label}>{t.earth.scenes[x.id].short}</span>
            </button>
          </li>
        ))}
      </ol>
      <button type="button" className={s.railStep} onClick={() => next && go(next.id)} disabled={!next} aria-label={t.earth.next}>
        <Icon name="arrowRight" size={20} />
      </button>
      {!calm && (
        <button type="button" className={s.play} aria-pressed={autoplay} onClick={onAutoplay}>
          <Icon name={autoplay ? 'pause' : 'play'} size={16} />{autoplay ? t.earth.pause : t.earth.play}
        </button>
      )}
    </nav>
  );
}

/** NASA Eyes (official, public, frameable) in a modal; "back to Earth" lands on the Nghệ An scene. */
function EyesDialog({ dialog, eyes, onClose, onDismiss }: {
  dialog: RefObject<HTMLDialogElement | null>; eyes: Eyes | null; onClose: (backToNgheAn: boolean) => void; onDismiss: () => void;
}) {
  const t = useT();
  const url = eyes ? eyesUrl(eyes.id) : undefined;
  return (
    <dialog ref={dialog} className={s.eyes} aria-label={eyes?.name ?? 'NASA Eyes'} onClose={onDismiss}>
      {eyes && url && (
        <div className={s.eyesInner}>
          <header className={s.eyesHead}>
            <div>
              <p className={s.small}>{t.earth.eyesBy}</p>
              <h2>{eyes.name}</h2>
            </div>
            <div className={s.eyesActions}>
              <a href={url} target="_blank" rel="noreferrer" className={s.srcLink}>{t.earth.newTab}<Icon name="arrowUpRight" size={16} /></a>
              <button type="button" className={s.backEarth} onClick={() => onClose(true)}><Icon name="leaf" size={18} />{t.earth.backToEarth}</button>
              <button type="button" className={s.closeBtn} onClick={() => onClose(false)} aria-label={t.common.close}><Icon name="close" size={20} /></button>
            </div>
          </header>
          <iframe className={s.eyesFrame} src={url} title={`NASA Eyes · ${eyes.name}`} allow="fullscreen" referrerPolicy="no-referrer" />
          <p className={s.small}>{t.earth.eyesNote}</p>
        </div>
      )}
    </dialog>
  );
}

function plainInsight(t: ReturnType<typeof useT>, f: ReturnType<typeof useFormat>, year: number, anomaly: number): string {
  if (anomaly < -0.1) return t.earth.plainDry(year, f.pct(-anomaly));
  if (anomaly > 0.1) return t.earth.plainWet(year, f.pct(anomaly));
  return t.earth.plainNormal(year);
}

function CellMetric({ cell, year, onCell, insight }: { cell: string; year: number; onCell: (c: string) => void; insight: boolean }) {
  const t = useT();
  const f = useFormat();
  const v = cellYear(cell, year);
  const ask = new URLSearchParams({ q: t.earth.askQ(year), hoi: '1', nam: String(year) }).toString();
  return (
    <div className={s.metric}>
      {/* the plain-language answer comes first; the numbers and the cell choice follow */}
      {insight && v && (
        <div className={s.insight}>
          <p className={s.insightText}>{plainInsight(t, f, year, v.anomaly)}</p>
          <p className={s.small}>{t.common.notForecast}. {t.earth.insightLimits}</p>
          <div className={s.insightLinks}>
            <Link to={`/tro-ly?${ask}`} className={s.askBtn}><Icon name="spark" size={18} />{t.earth.ask}</Link>
            <Link to={`/khoa-hoc?nam=${year}`} className={s.srcLink}>{t.earth.openScience}<Icon name="arrowRight" size={16} /></Link>
          </div>
        </div>
      )}
      <fieldset className={s.cells}>
        <legend>{t.earth.cellLabel}</legend>
        {CELLS.map((c) => (
          <label key={c} className={s.radio}>
            <input type="radio" name="cell" value={c} checked={cell === c} onChange={() => onCell(c)} />
            <span className="mono">{c.replace('_', '°N ')}°E</span>
          </label>
        ))}
      </fieldset>
      {v ? (
        <dl className={s.metricVals}>
          <dt>{t.earth.annualRain}</dt>
          <dd><SourceValue size="lg" sourceId="nasa-power" kind="derived" value={`${f.n(v.rain)} mm`} label={`${t.earth.annualRain} · ${year} · ${cell}`}
            detail={t.earth.rainDetail} chain={['nasa-power']} /></dd>
          <dt>{t.earth.vsNormal}</dt>
          <dd><SourceValue size="lg" sourceId="nasa-power" kind="derived" value={f.signedPct(v.anomaly, 0)} label={`${t.earth.vsNormal} · ${year} · ${cell}`}
            detail={t.earth.anomalyDetail} chain={['nasa-power']} /></dd>
        </dl>
      ) : <p className={s.small}>{t.common.noData}</p>}
      <div className={s.legend}>
        <span><i style={{ background: '#b8861b' }} />{t.earth.drier}</span>
        <span><i style={{ background: '#c9d1c6' }} />{t.earth.normal}</span>
        <span><i style={{ background: '#2e6f9b' }} />{t.earth.wetter}</span>
      </div>
      <p className={s.small}>{t.earth.cellNote}</p>
    </div>
  );
}
