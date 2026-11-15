// Two satellites cross the sky above the real Nghệ An border and NASA POWER grid, each sweeping a scan beam over
// the province. SVG only. The markup is the finished still (both satellites mid-pass, beams on, cells lit by their
// farmland share, border drawn); GSAP, through useCinema, animates *from* other values, so nothing is hidden at rest,
// in lite mode, under reduced motion or before the script runs. The loop can be paused (H1).
import { useEffect, useId, useRef, useState, type JSX, type RefObject } from 'react';
import { useSettings } from '../../app/settings';
import { geo } from '../../data';
import { Icon } from '../../design-system/Icon';
import { EASE, gsap, useCinema, ScrollTrigger } from '../../motion/cinema';
import { EARTH, Earth, FlagIcon, Satellite, SceneDefs, Space, type FlagKind } from './parts';
import s from './SatelliteScan.module.css';

export interface SatelliteScanLabels {
  satA: string;
  satB: string;
  province: string;
  caption: string;
  pause: string;
  play: string;
}

type Timeline = ReturnType<typeof gsap.timeline>;
type Pick = (selector: string) => Element[];

/* ---------- scene constants (viewBox 1600 × 900) ---------- */

const VIEW_H = 900;
const LOOP = 18; // seconds per loop
const GROUND = 2180; // distance from the Earth's centre to the surface ring the beams touch; the province sits on it
const GROUND_Y = EARTH.cy - GROUND;
const TILT = { sx: 2.7, sy: 1.65, lean: -0.12 } as const; // lays the flat map onto the curved surface, seen at an angle
const CELL_GAIN = 1.6; // cell fill opacity = farmland weight × gain (largest weight 0.47 → 0.76)
const CELL_STROKE = 0.3;
const CELLS_DIM_AT = 16.2;
const RAD = Math.PI / 180;

interface Pass {
  from: number;
  to: number;
  start: number;
  dur: number;
} // orbit angles in degrees, linear in time
interface Craft {
  key: 'a' | 'b';
  flag: FlagKind;
  radius: number;
  scale: number;
  rest: number;
  beam: number;
  pass: Pass;
}

// A flies west to east, lower and nearer; B flies east to west, higher and farther (drawn smaller), 4.6 s later. Each arc runs ±21° round the
// Earth in the 16:9 frame and ±12° in the 4:5 frame, so a satellite always enters and leaves just outside the edge.
const CRAFT_A: Craft = {
  key: 'a',
  flag: 'vn',
  radius: 2620,
  scale: 1,
  rest: -4,
  beam: 72,
  pass: { from: -21, to: 21, start: 0, dur: 13 },
};
const CRAFT_B: Craft = {
  key: 'b',
  flag: 'us',
  radius: 2790,
  scale: 0.72,
  rest: 5,
  beam: 58,
  pass: { from: 21, to: -21, start: 4.6, dur: 13 },
};
const DRAW_ORDER = [CRAFT_B, CRAFT_A] as const;

interface Fleet {
  a: Craft;
  b: Craft;
}
const shorter = (c: Craft): Craft => ({
  ...c,
  pass: { ...c.pass, from: Math.sign(c.pass.from) * 12, to: Math.sign(c.pass.to) * 12 },
});
const FLEET: Record<'wide' | 'narrow', Fleet> = {
  wide: { a: CRAFT_A, b: CRAFT_B },
  narrow: { a: shorter(CRAFT_A), b: shorter(CRAFT_B) },
};

/* ---------- geometry: the home page's projection, laid onto the Earth ---------- */

interface SceneCell {
  id: string;
  points: string;
  cx: number;
  alpha: number;
}
interface SceneGeo {
  outline: string[];
  cells: SceneCell[];
  minX: number;
  maxX: number;
  minY: number;
  maxY: number;
}

const pointList = (pts: [number, number][]) => pts.map(([x, y]) => `${x.toFixed(1)},${y.toFixed(1)}`).join(' ');

function buildScene(): SceneGeo {
  const [minLon, minLat, maxLon, maxLat] = geo.bounds;
  // Same projection as the Observatory (k = cos 19.3°, 100 units per degree), centred on the province.
  const k = Math.cos(19.3 * RAD);
  const midLon = (minLon + maxLon) / 2;
  const midLat = (minLat + maxLat) / 2;
  const toScene = (lon: number, lat: number): [number, number] => {
    const u = (lon - midLon) * k * 100 * TILT.sx;
    const v = (midLat - lat) * 100 * TILT.sy;
    return [EARTH.cx + u + TILT.lean * v, GROUND_Y + v];
  };
  const rings = geo.outline.map((ring) => ring.map(([lon, lat]) => toScene(lon, lat)));
  const xs = rings.flat().map((p) => p[0]);
  const ys = rings.flat().map((p) => p[1]);
  const cells = geo.grid.map((c) => ({
    id: c.id,
    points: pointList([
      toScene(c.lon - 0.3125, c.lat + 0.25),
      toScene(c.lon + 0.3125, c.lat + 0.25),
      toScene(c.lon + 0.3125, c.lat - 0.25),
      toScene(c.lon - 0.3125, c.lat - 0.25),
    ]),
    cx: toScene(c.lon, c.lat)[0],
    alpha: c.weight * CELL_GAIN,
  }));
  return {
    outline: rings.map(pointList),
    cells,
    minX: Math.min(...xs),
    maxX: Math.max(...xs),
    minY: Math.min(...ys),
    maxY: Math.max(...ys),
  };
}

const SCENE = buildScene();

const clamp = (v: number, lo: number, hi: number) => Math.min(hi, Math.max(lo, v));
/** Centre of a beam's footprint when its satellite is `angle` degrees round the orbit. */
const footprint = (angle: number): [number, number] => [
  EARTH.cx + GROUND * Math.sin(angle * RAD),
  EARTH.cy - GROUND * Math.cos(angle * RAD),
];
const angleAt = (x: number) => Math.asin(clamp((x - EARTH.cx) / GROUND, -1, 1)) / RAD;
const timeAt = (p: Pass, angle: number) => p.start + ((angle - p.from) / (p.to - p.from)) * p.dur;
const orbit = (angle: number) => `rotate(${angle} ${EARTH.cx} ${EARTH.cy})`;
const shift = (x: number) => `translate(${x.toFixed(2)} 0)`;
/** Where the scan line sits so it crosses the footprint (the line leans with the province). */
const scanX = (angle: number) => {
  const [x, y] = footprint(angle);
  return x - TILT.lean * (y - GROUND_Y);
};

interface PassWindow {
  xIn: number;
  xOut: number;
  aIn: number;
  aOut: number;
  tIn: number;
  tOut: number;
}

/** When a satellite's footprint crosses the province (plus `margin` scene units), in scene x, orbit angle, seconds. */
function passWindow(c: Craft, margin = 30): PassWindow {
  const west = SCENE.minX - margin;
  const east = SCENE.maxX + margin;
  const eastward = c.pass.to > c.pass.from;
  const xIn = eastward ? west : east;
  const xOut = eastward ? east : west;
  const aIn = angleAt(xIn);
  const aOut = angleAt(xOut);
  return { xIn, xOut, aIn, aOut, tIn: timeAt(c.pass, aIn), tOut: timeAt(c.pass, aOut) };
}

/** Time at which a satellite's scan line reaches scene x (clamped to its pass over the province). */
function timeOver(c: Craft, x: number) {
  const w = passWindow(c);
  const a = clamp(angleAt(x), Math.min(w.aIn, w.aOut), Math.max(w.aIn, w.aOut));
  return timeAt(c.pass, a);
}

/* ---------- motion (only ever called inside useCinema) ---------- */

/** Fade on, hold, fade off. Every animated property ends a loop where it began, so the repeat is seamless. */
function fadeWindow(tl: Timeline, targets: Element[], on: number, off: number, d: number) {
  if (!targets.length) return;
  tl.fromTo(targets, { opacity: 0 }, { opacity: 1, duration: d }, on);
  tl.to(targets, { opacity: 0, duration: d }, off);
}

function addPass(tl: Timeline, q: Pick, c: Craft) {
  const w = passWindow(c);
  const span = w.tOut - w.tIn;
  const scan = q(`[data-scan="${c.key}"]`);
  tl.fromTo(
    q(`[data-orbit="${c.key}"]`),
    { attr: { transform: orbit(c.pass.from) } },
    { attr: { transform: orbit(c.pass.to) }, duration: c.pass.dur, ease: 'none' },
    c.pass.start,
  );
  fadeWindow(tl, q(`[data-beam="${c.key}"]`), w.tIn - 1.4, w.tOut + 0.2, 1.2);
  fadeWindow(tl, [...scan, ...q(`[data-hud-mark="${c.key}"]`)], w.tIn - 0.25, w.tOut - 0.15, 0.4);
  tl.fromTo(
    scan,
    { attr: { transform: shift(w.xIn) } },
    { attr: { transform: shift(w.xOut) }, duration: span, ease: 'none' },
    w.tIn,
  );
}

/** A's beam lights each cell to its farmland share; B's beam brushes its border; all dim before the loop ends. */
function addCells(tl: Timeline, q: Pick, fleet: Fleet) {
  SCENE.cells.forEach((cell) => {
    const el = q(`[data-cell="${cell.id}"]`);
    if (!el.length) return;
    if (cell.alpha > 0) {
      tl.fromTo(el, { fillOpacity: 0 }, { fillOpacity: cell.alpha, duration: 1 }, timeOver(fleet.a, cell.cx) - 0.3);
      tl.to(el, { fillOpacity: 0, duration: 1.4 }, CELLS_DIM_AT);
    }
    tl.fromTo(
      el,
      { strokeOpacity: CELL_STROKE },
      { strokeOpacity: 0.9, duration: 0.6, yoyo: true, repeat: 1 },
      timeOver(fleet.b, cell.cx) - 0.3,
    );
  });
}

/** A few stars dim and return, slowly (one cycle every 4.5 to 9 s), a whole number of times per loop. */
function addTwinkles(tl: Timeline, q: Pick) {
  q('[data-twinkle]').forEach((el, i) => {
    const o = Number(el.getAttribute('opacity')) || 0.6;
    const cycles = 2 + (i % 3);
    tl.fromTo(
      el,
      { opacity: o },
      { opacity: o * 0.3, duration: LOOP / (2 * cycles), repeat: 2 * cycles - 1, yoyo: true },
      0,
    );
  });
}

function buildTimeline(scope: HTMLElement, fleet: Fleet): Timeline {
  const q: Pick = gsap.utils.selector(scope);
  const loop = gsap.timeline({ repeat: -1, defaults: { ease: 'sine.inOut' } });
  addPass(loop, q, fleet.a);
  addPass(loop, q, fleet.b);
  addCells(loop, q, fleet);
  addTwinkles(loop, q);
  loop.set({}, {}, LOOP);

  // Once, on the first pass of A: the border traces itself, then the province's name appears.
  const a = passWindow(fleet.a);
  const master = gsap.timeline();
  master.add(loop, 0);
  // autoRound: false, or GSAP rounds the dash offset (a px value) to 0 or 1 and the border pops in instead of tracing.
  master.from(
    q('[data-outline]'),
    { strokeDashoffset: 1, fillOpacity: 0, autoRound: false, duration: a.tOut - a.tIn + 0.6, ease: EASE.calm },
    a.tIn - 0.3,
  );
  master.from(q('[data-place]'), { opacity: 0, y: 10, duration: 1.2, ease: EASE.calm }, a.tOut);

  return master;
}

/* ---------- drawing ---------- */

function Province() {
  return (
    <g>
      {SCENE.cells.map((c) => (
        <polygon
          key={c.id}
          points={c.points}
          className={s.cell}
          data-cell={c.id}
          strokeOpacity={CELL_STROKE}
          style={{ fillOpacity: c.alpha }}
        />
      ))}
      {SCENE.outline.map((pts, i) => (
        <polygon key={i} points={pts} className={s.outline} pathLength={1} data-outline />
      ))}
    </g>
  );
}

function Orbits() {
  return (
    <g fill="none" stroke="#f3f1e8" strokeOpacity={0.08} strokeWidth={1.2} strokeDasharray="3 12">
      {DRAW_ORDER.map((c) => (
        <circle key={c.key} cx={EARTH.cx} cy={EARTH.cy} r={c.radius} />
      ))}
    </g>
  );
}

function Beam({ c, uid }: { c: Craft; uid: string }) {
  const apex = EARTH.cy - c.radius + 46 * c.scale;
  const cone = (hw: number) =>
    `${EARTH.cx - 3},${apex} ${EARTH.cx + 3},${apex} ${EARTH.cx + hw},${GROUND_Y} ${EARTH.cx - hw},${GROUND_Y}`;
  return (
    <g data-orbit={c.key} transform={orbit(c.rest)}>
      <g data-beam={c.key}>
        <polygon points={cone(c.beam)} fill={`url(#${uid}-beam)`} />
        <polygon points={cone(c.beam * 0.3)} fill={`url(#${uid}-beam)`} />
        <ellipse
          cx={EARTH.cx}
          cy={GROUND_Y}
          rx={c.beam}
          ry={c.beam * 0.24}
          fill="#e8b94e"
          fillOpacity={0.14}
          stroke="#f1d38c"
          strokeOpacity={0.6}
          strokeWidth={1.5}
        />
      </g>
    </g>
  );
}

function ScanLines({ uid }: { uid: string }) {
  const top = SCENE.minY - 14;
  const bottom = SCENE.maxY + 14;
  const lean = (y: number) => TILT.lean * (y - GROUND_Y);
  const band = (hw: number) =>
    `${lean(top) - hw},${top} ${lean(top) + hw},${top} ${lean(bottom) + hw},${bottom} ${lean(bottom) - hw},${bottom}`;
  return (
    <g clipPath={`url(#${uid}-prov)`}>
      {DRAW_ORDER.map((c) => (
        <g key={c.key} data-scan={c.key} transform={shift(scanX(c.rest))}>
          <polygon points={band(28)} fill={`url(#${uid}-swath)`} />
          <line
            x1={lean(top)}
            y1={top}
            x2={lean(bottom)}
            y2={bottom}
            stroke="#f1d38c"
            strokeWidth={2.2}
            strokeLinecap="round"
          />
        </g>
      ))}
    </g>
  );
}

function Orbiter({ c, uid }: { c: Craft; uid: string }) {
  return (
    <g data-orbit={c.key} transform={orbit(c.rest)}>
      <g transform={`translate(${EARTH.cx} ${EARTH.cy - c.radius}) scale(${c.scale})`}>
        <Satellite uid={uid} flag={c.flag} dir={c.pass.to > c.pass.from ? 1 : -1} />
      </g>
    </g>
  );
}

function SceneSvg({ uid }: { uid: string }) {
  return (
    <svg
      className={s.svg}
      viewBox={`0 0 1600 ${VIEW_H}`}
      preserveAspectRatio="xMidYMid slice"
      aria-hidden="true"
      focusable="false"
    >
      <SceneDefs uid={uid} clip={SCENE.outline} />
      <Space uid={uid} />
      <Earth uid={uid} />
      <Province />
      <Orbits />
      {DRAW_ORDER.map((c) => (
        <Beam key={c.key} c={c} uid={uid} />
      ))}
      <ScanLines uid={uid} />
      {DRAW_ORDER.map((c) => (
        <Orbiter key={c.key} c={c} uid={uid} />
      ))}
    </svg>
  );
}

/** Legend: each satellite's flag and name (no coordinates: the drawn orbits are illustrations, H5). */
function Telemetry({ labels }: { labels: SatelliteScanLabels }) {
  const rows = [
    { c: CRAFT_A, name: labels.satA },
    { c: CRAFT_B, name: labels.satB },
  ];
  return (
    <div className={s.panel}>
      <table className={s.hud}>
        <tbody>
          {rows.map(({ c, name }) => (
            <tr key={c.key}>
              <th scope="row">
                <span className={s.name}>
                  <span className={s.mark} data-hud-mark={c.key} aria-hidden="true" />
                  <FlagIcon kind={c.flag} className={s.flag} />
                  {name}
                </span>
              </th>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

/** True when the stage is the tall 4:5 frame (it follows the figure's width, not the window's). */
function useNarrowStage(stage: RefObject<HTMLElement | null>) {
  const [narrow, setNarrow] = useState(false);
  useEffect(() => {
    const el = stage.current;
    if (!el || typeof ResizeObserver === 'undefined') return;
    const ro = new ResizeObserver(([entry]) => {
      if (entry) setNarrow(entry.contentRect.width < entry.contentRect.height * 1.2);
    });
    ro.observe(el);
    return () => ro.disconnect();
  }, [stage]);
  return narrow;
}

export function SatelliteScan({ labels, className }: { labels: SatelliteScanLabels; className?: string }): JSX.Element {
  const { calm } = useSettings();
  const uid = `ss${useId().replace(/[^A-Za-z0-9_-]/g, '')}`;
  const root = useRef<HTMLElement>(null);
  const stage = useRef<HTMLDivElement>(null);
  const narrow = useNarrowStage(stage);
  const timeline = useRef<Timeline | null>(null);
  const pausedRef = useRef(false);
  const [paused, setPaused] = useState(false);

  useCinema(root, () => {
    if (!root.current) return;
    const tl = buildTimeline(root.current, narrow ? FLEET.narrow : FLEET.wide);
    timeline.current = tl;
    // play only while on screen, and never against the visitor's pause
    const onScreen = () => ScrollTrigger.isInViewport(root.current as Element);
    tl.paused(pausedRef.current || !onScreen());
    ScrollTrigger.create({
      trigger: root.current,
      start: 'top bottom',
      end: 'bottom top',
      onToggle: (self) => {
        if (!pausedRef.current) tl.paused(!self.isActive);
      },
    });
  }, [narrow]);

  const toggle = () => {
    const next = !pausedRef.current;
    pausedRef.current = next;
    setPaused(next);
    timeline.current?.paused(next);
  };

  return (
    <figure ref={root} className={className ? `${s.root} ${className}` : s.root}>
      <div ref={stage} className={s.stage}>
        <SceneSvg uid={uid} />
        <p className={s.place} data-place style={{ top: `${(((SCENE.maxY + 14) / VIEW_H) * 100).toFixed(2)}%` }}>
          <span>{labels.province}</span>
        </p>
        {!calm && (
          <button type="button" className={s.motion} onClick={toggle}>
            <Icon name={paused ? 'play' : 'pause'} size={18} />
            {paused ? labels.play : labels.pause}
          </button>
        )}
      </div>
      <Telemetry labels={labels} />
      <figcaption className={s.caption}>{labels.caption}</figcaption>
    </figure>
  );
}
