// Drawings for the satellite scan: space, the Earth, two satellites and their flag decals. Pure SVG with no text
// and no agency marks (no NASA insignia or logotype); every word on screen comes from the component's labels.
export type FlagKind = 'vn' | 'us';

/** The Earth in scene units (viewBox 1600 × 900): a large circle whose top edge is the horizon at y = 470. */
export const EARTH = { cx: 800, cy: 2870, r: 2400 } as const;

const url = (uid: string, name: string) => `url(#${uid}-${name})`;

/* ---------- flags ---------- */

function starPoints(cx: number, cy: number, r: number): string {
  const inner = r * 0.382;
  return Array.from({ length: 10 }, (_, i) => {
    const a = -Math.PI / 2 + (i * Math.PI) / 5;
    const d = i % 2 === 0 ? r : inner;
    return `${(cx + d * Math.cos(a)).toFixed(2)},${(cy + d * Math.sin(a)).toFixed(2)}`;
  }).join(' ');
}

/** Flag of Vietnam, 3:2: red field, five-pointed yellow star whose points touch a circle of 0.3 × the height. */
export function VietnamFlag({ w }: { w: number }) {
  const h = (w * 2) / 3;
  return (
    <g>
      <rect width={w} height={h} fill="#DA251D" />
      <polygon points={starPoints(w / 2, h / 2, h * 0.3)} fill="#FFFF00" />
    </g>
  );
}

// Simplified stars: eleven dots on the canton, enough to read as the flag at decal size.
const CANTON_DOTS: [number, number][] = [
  [0.17, 0.2],
  [0.39, 0.2],
  [0.61, 0.2],
  [0.83, 0.2],
  [0.28, 0.5],
  [0.5, 0.5],
  [0.72, 0.5],
  [0.17, 0.8],
  [0.39, 0.8],
  [0.61, 0.8],
  [0.83, 0.8],
];

/** Simplified flag of the United States, 19:10: thirteen stripes and a blue canton. */
export function UsFlag({ w }: { w: number }) {
  const h = w / 1.9;
  const sh = h / 13;
  const cw = w * 0.4;
  const ch = sh * 7;
  return (
    <g>
      <rect width={w} height={h} fill="#FFFFFF" />
      {Array.from({ length: 7 }, (_, i) => (
        <rect key={i} y={i * 2 * sh} width={w} height={sh} fill="#B22234" />
      ))}
      <rect width={cw} height={ch} fill="#3C3B6E" />
      {CANTON_DOTS.map(([dx, dy]) => (
        <circle key={`${dx}-${dy}`} cx={dx * cw} cy={dy * ch} r={sh * 0.3} fill="#FFFFFF" />
      ))}
    </g>
  );
}

/** A flag as a small inline picture for the HTML legend (decorative: the satellite's name sits next to it). */
export function FlagIcon({ kind, className }: { kind: FlagKind; className?: string }) {
  const vn = kind === 'vn';
  return (
    <svg
      viewBox={vn ? '0 0 30 20' : '0 0 38 20'}
      width={vn ? 27 : 34}
      height={18}
      className={className}
      aria-hidden="true"
      focusable="false"
    >
      {vn ? <VietnamFlag w={30} /> : <UsFlag w={38} />}
    </svg>
  );
}

/* ---------- satellite (local units: body 56 × 64 centred on 0,0; +y points at the Earth) ---------- */

const PANEL = { inner: 40, outer: 120, half: 16, cols: 8, rows: 4 } as const;

function cellGrid(x0: number): string {
  const w = PANEL.outer - PANEL.inner;
  const h = PANEL.half * 2;
  const v = Array.from({ length: PANEL.cols - 1 }, (_, i) => `M${x0 + ((i + 1) * w) / PANEL.cols} ${-PANEL.half}v${h}`);
  const hz = Array.from(
    { length: PANEL.rows - 1 },
    (_, i) => `M${x0} ${-PANEL.half + ((i + 1) * h) / PANEL.rows}h${w}`,
  );
  return [...v, ...hz].join('');
}

function Wing({ uid, side }: { uid: string; side: 1 | -1 }) {
  const x0 = side > 0 ? PANEL.inner : -PANEL.outer;
  const w = PANEL.outer - PANEL.inner;
  return (
    <g>
      <rect x={side > 0 ? 28 : -40} y={-2} width={12} height={4} fill="#a6ae9f" />
      <rect
        x={x0}
        y={-PANEL.half}
        width={w}
        height={PANEL.half * 2}
        rx={1.5}
        fill={url(uid, 'panel')}
        stroke="#c8d0c6"
        strokeWidth={1.1}
      />
      <path d={cellGrid(x0)} fill="none" stroke="#bfd0cc" strokeOpacity={0.34} strokeWidth={0.7} />
      <rect x={x0} y={-PANEL.half} width={w} height={PANEL.half * 2} rx={1.5} fill={url(uid, 'sheen')} />
      <path d={`M${x0 + w / 2} ${-PANEL.half}v${PANEL.half * 2}`} stroke="#c8d0c6" strokeWidth={1.3} />
    </g>
  );
}

function Bus({ uid }: { uid: string }) {
  return (
    <g>
      <rect x={-28} y={-32} width={56} height={64} rx={3} fill={url(uid, 'foil')} stroke="#7d570b" strokeWidth={0.9} />
      <path
        d="M-24 -18l8 3 6-2 9 4 9-3 8 2M-25 12l7-2 8 3 7-2 11 3 6-1M-14 19l6-3 8 2"
        fill="none"
        stroke="#7d570b"
        strokeOpacity={0.55}
        strokeWidth={0.8}
      />
      <rect x={-28} y={-32} width={56} height={9} rx={2} fill="#c8d0c6" />
      <path d="M-24 -27.5h48" stroke="#8ea6a1" strokeWidth={0.8} />
      <rect x={-28} y={23} width={56} height={9} rx={2} fill="#a6ae9f" />
      <rect x={-10} y={-39} width={10} height={7} fill="#26382b" stroke="#c8d0c6" strokeWidth={0.8} />
      <circle cx={-5} cy={-35.5} r={2} fill="#0b110d" stroke="#f1d38c" strokeWidth={0.6} />
    </g>
  );
}

function Antennas() {
  return (
    <g stroke="#c8d0c6" strokeWidth={1.1} strokeLinecap="round">
      <path d="M14 -32L19 -47" fill="none" />
      <path d="M7 -52A13 5.5 0 0 0 33 -52Z" fill="#edf0ea" stroke="#a6ae9f" />
      <path d="M20 -52V-60" fill="none" />
      <circle cx={20} cy={-61} r={1.5} fill="#f1d38c" stroke="none" />
      <path d="M-17 -32L-27 -64" fill="none" strokeWidth={0.9} />
      <circle cx={-27.3} cy={-65} r={1.5} fill="#c8d0c6" stroke="none" />
    </g>
  );
}

/** Two small thrusters on the trailing side, between the body and the solar wing. */
function Thrusters() {
  return (
    <g fill="#7f8a80" stroke="#c8d0c6" strokeWidth={0.7} strokeLinejoin="round">
      <polygon points="-28,-19 -28,-12 -36,-10 -36,-21" />
      <polygon points="-28,12 -28,19 -36,21 -36,10" />
    </g>
  );
}

/** The Earth-facing sensor the beam comes out of. */
function Sensor() {
  return (
    <g>
      <rect x={-11} y={32} width={22} height={10} rx={1.5} fill="#26382b" stroke="#a6ae9f" strokeWidth={0.8} />
      <ellipse cx={0} cy={43.5} rx={10} ry={3.2} fill="#0b110d" stroke="#f1d38c" strokeWidth={0.9} />
      <ellipse cx={-3.5} cy={43} rx={2.8} ry={0.9} fill="#f1d38c" opacity={0.8} />
    </g>
  );
}

function Decal({ flag }: { flag: FlagKind }) {
  const w = flag === 'vn' ? 30 : 32;
  const h = flag === 'vn' ? 20 : 32 / 1.9;
  return (
    <g transform={`translate(${-w / 2} ${(-4 - h / 2).toFixed(2)})`}>
      {flag === 'vn' ? <VietnamFlag w={w} /> : <UsFlag w={w} />}
      <rect width={w} height={h} fill="none" stroke="#050b08" strokeOpacity={0.5} strokeWidth={0.7} />
    </g>
  );
}

/** One satellite. `dir` mirrors the hardware so the thrusters trail; the flag decal is never mirrored. */
export function Satellite({ uid, flag, dir }: { uid: string; flag: FlagKind; dir: 1 | -1 }) {
  return (
    <g>
      <g transform={dir < 0 ? 'scale(-1 1)' : undefined}>
        <Wing uid={uid} side={-1} />
        <Wing uid={uid} side={1} />
        <Thrusters />
        <Bus uid={uid} />
        <Antennas />
        <Sensor />
      </g>
      <Decal flag={flag} />
    </g>
  );
}

/* ---------- space and Earth ---------- */

function mulberry32(seed: number) {
  let a = seed;
  return () => {
    a = (a + 0x6d2b79f5) | 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

interface Star {
  x: number;
  y: number;
  r: number;
  o: number;
  c: string;
  twinkle: boolean;
}

// A fixed starfield: the same seed gives the same sky on every render and on the server.
const STARS: Star[] = (() => {
  const rnd = mulberry32(1930);
  let twinkles = 0;
  return Array.from({ length: 130 }, () => {
    const x = rnd() * 1600;
    const y = rnd() * 640;
    const r = 0.9 + rnd() ** 3 * 2;
    const o = 0.28 + rnd() * 0.6;
    const pick = rnd();
    const c = pick < 0.12 ? '#f1d38c' : pick < 0.22 ? '#bfd0cc' : '#f3f1e8';
    const twinkle = r > 1.7 && twinkles < 9;
    if (twinkle) twinkles += 1;
    return { x, y, r, o, c, twinkle };
  });
})();

export function Space({ uid }: { uid: string }) {
  return (
    <g>
      <rect width={1600} height={900} fill={url(uid, 'sky')} />
      <rect width={1600} height={900} fill={url(uid, 'haze')} />
      <g>
        {STARS.map((st, i) => (
          <circle
            key={i}
            cx={st.x.toFixed(1)}
            cy={st.y.toFixed(1)}
            r={st.r.toFixed(2)}
            fill={st.c}
            opacity={st.o.toFixed(2)}
            data-twinkle={st.twinkle ? '' : undefined}
          />
        ))}
      </g>
    </g>
  );
}

// Faint parallels (concentric arcs) and meridians (lines running to the Earth's centre) give the surface depth.
const GRATICULE = (() => {
  const { cx, cy, r } = EARTH;
  const at = (rad: number, deg: number) => {
    const a = (deg * Math.PI) / 180;
    return `${(cx + rad * Math.sin(a)).toFixed(1)} ${(cy - rad * Math.cos(a)).toFixed(1)}`;
  };
  const arcs = [60, 150, 270, 420, 600].map((d) => `M${at(r - d, -26)}A${r - d} ${r - d} 0 0 1 ${at(r - d, 26)}`);
  const meridians = Array.from({ length: 13 }, (_, i) => -24 + i * 4).map(
    (deg) => `M${at(r, deg)}L${at(r - 720, deg)}`,
  );
  return [...arcs, ...meridians].join('');
})();

export function Earth({ uid }: { uid: string }) {
  const { cx, cy, r } = EARTH;
  return (
    <g>
      <circle cx={cx} cy={cy} r={r} fill={url(uid, 'earth')} />
      <circle cx={cx} cy={cy} r={r} fill={url(uid, 'shade')} />
      <path d={GRATICULE} fill="none" stroke="#bfd0cc" strokeOpacity={0.07} strokeWidth={1.2} />
      <circle cx={cx} cy={cy} r={r + 80} fill={url(uid, 'atmo')} />
      <circle cx={cx} cy={cy} r={r} fill="none" stroke="#bfd0cc" strokeOpacity={0.38} strokeWidth={1.6} />
    </g>
  );
}

/* ---------- shared definitions ---------- */

function Stop({ at, color, alpha = 1 }: { at: number; color: string; alpha?: number }) {
  return <stop offset={at} stopColor={color} stopOpacity={alpha} />;
}

function SkyDefs({ uid }: { uid: string }) {
  const { cx, cy, r } = EARTH;
  const R = r + 80;
  return (
    <>
      <linearGradient id={`${uid}-sky`} x1="0" y1="0" x2="0" y2="1">
        <Stop at={0} color="#050b08" />
        <Stop at={0.6} color="#0a1a11" />
        <Stop at={1} color="#0f2a1b" />
      </linearGradient>
      <radialGradient id={`${uid}-haze`} gradientUnits="userSpaceOnUse" cx={220} cy={520} r={820}>
        <Stop at={0} color="#e8b94e" alpha={0.12} />
        <Stop at={0.55} color="#e8b94e" alpha={0.035} />
        <Stop at={1} color="#e8b94e" alpha={0} />
      </radialGradient>
      <radialGradient id={`${uid}-earth`} gradientUnits="userSpaceOnUse" cx={cx} cy={470} r={1000}>
        <Stop at={0} color="#1c3826" />
        <Stop at={0.5} color="#10251a" />
        <Stop at={1} color="#08130c" />
      </radialGradient>
      <linearGradient id={`${uid}-shade`} gradientUnits="userSpaceOnUse" x1={0} y1={0} x2={1600} y2={0}>
        <Stop at={0} color="#e8b94e" alpha={0.06} />
        <Stop at={0.45} color="#e8b94e" alpha={0} />
        <Stop at={1} color="#050b08" alpha={0.5} />
      </linearGradient>
      <radialGradient id={`${uid}-atmo`} gradientUnits="userSpaceOnUse" cx={cx} cy={cy} r={R}>
        <Stop at={(r - 60) / R} color="#8ea6a1" alpha={0} />
        <Stop at={r / R} color="#8ea6a1" alpha={0.26} />
        <Stop at={(r + 14) / R} color="#8ea6a1" alpha={0.12} />
        <Stop at={1} color="#8ea6a1" alpha={0} />
      </radialGradient>
    </>
  );
}

function CraftDefs({ uid }: { uid: string }) {
  return (
    <>
      <linearGradient id={`${uid}-foil`} x1="0" y1="0" x2="1" y2="1">
        <Stop at={0} color="#f7ebc9" />
        <Stop at={0.3} color="#e8b94e" />
        <Stop at={0.62} color="#c38f27" />
        <Stop at={1} color="#7d570b" />
      </linearGradient>
      <linearGradient id={`${uid}-panel`} x1="0" y1="0" x2="0" y2="1">
        <Stop at={0} color="#24496b" />
        <Stop at={1} color="#0f2438" />
      </linearGradient>
      <linearGradient id={`${uid}-sheen`} x1="0" y1="0" x2="1" y2="1">
        <Stop at={0} color="#ffffff" alpha={0.2} />
        <Stop at={0.5} color="#ffffff" alpha={0} />
      </linearGradient>
      <linearGradient id={`${uid}-beam`} x1="0" y1="0" x2="0" y2="1">
        <Stop at={0} color="#f1d38c" alpha={0.36} />
        <Stop at={0.65} color="#e8b94e" alpha={0.15} />
        <Stop at={1} color="#e8b94e" alpha={0.07} />
      </linearGradient>
      <linearGradient id={`${uid}-swath`} x1="0" y1="0" x2="1" y2="0">
        <Stop at={0} color="#e8b94e" alpha={0} />
        <Stop at={0.5} color="#e8b94e" alpha={0.28} />
        <Stop at={1} color="#e8b94e" alpha={0} />
      </linearGradient>
    </>
  );
}

/** Gradients for the whole scene and the province clip (ids are prefixed so two scenes can share a page). */
export function SceneDefs({ uid, clip }: { uid: string; clip: string[] }) {
  return (
    <defs>
      <SkyDefs uid={uid} />
      <CraftDefs uid={uid} />
      <clipPath id={`${uid}-prov`}>
        {clip.map((pts, i) => (
          <polygon key={i} points={pts} />
        ))}
      </clipPath>
    </defs>
  );
}
