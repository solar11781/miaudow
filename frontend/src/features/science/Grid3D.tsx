import { useEffect, useMemo, useRef, useState, type KeyboardEvent, type PointerEvent } from 'react';
import { geo, hazards, type RuleCode } from '../../data';
import { MAP_PLACES } from '../../data/places';
import { cellMagnitude, cellMet, RULES } from '../../domain/hazards';
import { Icon } from '../../design-system/Icon';
import { useFormat, useSettings, useT } from '../../app/settings';
import s from './Grid3D.module.css';

const PX_PER_DEG = 168;
const K_LON = Math.cos((19.3 * Math.PI) / 180);
const HMAX = 115;
const DEFAULT_VIEW = { rx: 55, rz: -24 };

export function Grid3D({
  rule,
  year,
  selected,
  onSelect,
  forceFlat = false,
}: {
  rule: RuleCode;
  year: number;
  selected: string;
  onSelect: (id: string) => void;
  forceFlat?: boolean;
}) {
  const t = useT();
  const f = useFormat();
  const { calm, lang } = useSettings();
  const [view3d, setView3d] = useState(true);
  const [rot, setRot] = useState(DEFAULT_VIEW);
  const [scale, setScale] = useState(1);
  const stage = useRef<HTMLDivElement>(null);
  const drag = useRef<{ x: number; y: number; rx: number; rz: number; moved: boolean } | null>(null);
  const flat = !view3d || calm || forceFlat;

  const box = useMemo(() => {
    const lons = geo.grid.map((c) => c.lon);
    const lats = geo.grid.map((c) => c.lat);
    const minLon = Math.min(...lons) - 0.3125,
      maxLon = Math.max(...lons) + 0.3125;
    const minLat = Math.min(...lats) - 0.25,
      maxLat = Math.max(...lats) + 0.25;
    const W = (maxLon - minLon) * PX_PER_DEG * K_LON,
      H = (maxLat - minLat) * PX_PER_DEG;
    const px = (lon: number, lat: number) =>
      [(lon - minLon) * PX_PER_DEG * K_LON, (maxLat - lat) * PX_PER_DEG] as const;
    return { W, H, px };
  }, []);

  const magKey = RULES[rule].magnitude;
  const magMax = useMemo(() => Math.max(1, ...Object.values(hazards.magnitudes[magKey]).flat()), [magKey]);

  useEffect(() => {
    const el = stage.current;
    if (!el) return;
    const fit = () =>
      setScale(Math.min(1, (el.clientWidth - 32) / (box.W + 80), (el.clientHeight - 60) / (box.H + 140)));
    fit();
    const ro = new ResizeObserver(fit);
    ro.observe(el);
    return () => ro.disconnect();
  }, [box]);

  const onDown = (e: PointerEvent) => {
    if (flat || (e.target as HTMLElement).closest('button')) return;
    drag.current = { x: e.clientX, y: e.clientY, rx: rot.rx, rz: rot.rz, moved: false };
    (e.currentTarget as HTMLElement).setPointerCapture(e.pointerId);
  };
  const onMove = (e: PointerEvent) => {
    const d = drag.current;
    if (!d) return;
    const dx = e.clientX - d.x,
      dy = e.clientY - d.y;
    if (Math.abs(dx) + Math.abs(dy) > 3) d.moved = true;
    setRot({ rz: d.rz + dx * 0.35, rx: Math.max(18, Math.min(72, d.rx - dy * 0.25)) });
  };
  const onUp = () => {
    drag.current = null;
  };
  const onKey = (e: KeyboardEvent) => {
    if (flat) return;
    const step = { ArrowLeft: [0, -8], ArrowRight: [0, 8], ArrowUp: [-4, 0], ArrowDown: [4, 0] }[e.key];
    if (!step) return;
    e.preventDefault();
    setRot((r) => ({ rx: Math.max(18, Math.min(72, r.rx + (step[0] ?? 0))), rz: r.rz + (step[1] ?? 0) }));
  };

  const outline = geo.outline.map((ring) => ring.map(([lon, lat]) => box.px(lon, lat).join(',')).join(' '));
  const cw = 0.625 * PX_PER_DEG * K_LON,
    ch = 0.5 * PX_PER_DEG;
  const color = RULES[rule].color;

  return (
    <div className={s.wrap}>
      <div
        ref={stage}
        className={[s.stage, flat ? s.flat : ''].join(' ')}
        onPointerDown={onDown}
        onPointerMove={onMove}
        onPointerUp={onUp}
        onPointerCancel={onUp}
        onKeyDown={onKey}
        tabIndex={0}
        role="group"
        aria-label={`${t.science.mapTitle}. ${flat ? t.science.flatHint : t.science.dragHint}`}
      >
        <div className={s.controls}>
          {!forceFlat && (
            <>
              <button
                type="button"
                onClick={() => setRot((r) => ({ ...r, rz: r.rz - 30 }))}
                disabled={flat}
                aria-label={t.science.rotateLeft}
              >
                <Icon name="rotateL" size={18} />
              </button>
              <button
                type="button"
                onClick={() => setRot((r) => ({ ...r, rz: r.rz + 30 }))}
                disabled={flat}
                aria-label={t.science.rotateRight}
              >
                <Icon name="rotateR" size={18} />
              </button>
              <button type="button" onClick={() => setRot(DEFAULT_VIEW)} disabled={flat} aria-label={t.science.reset}>
                <Icon name="reset" size={18} />
              </button>
              <button
                type="button"
                className={s.mode}
                aria-pressed={!flat}
                onClick={() => setView3d((v) => !v)}
                disabled={calm}
              >
                {flat ? t.science.view2d : t.science.view3d}
              </button>
            </>
          )}
        </div>
        <div className={s.fit} style={{ transform: `scale(${scale})` }}>
          <div
            className={s.scene}
            style={{
              width: box.W,
              height: box.H,
              left: -box.W / 2,
              top: -box.H / 2,
              transform: flat ? 'none' : `rotateX(${rot.rx}deg) rotateZ(${rot.rz}deg)`,
            }}
          >
            <svg
              className={s.plane}
              viewBox={`-40 -40 ${box.W + 80} ${box.H + 80}`}
              style={{ left: -40, top: -40, width: box.W + 80, height: box.H + 80 }}
              aria-hidden="true"
            >
              <defs>
                <pattern id="hatch" width="7" height="7" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">
                  <line x1="0" y1="0" x2="0" y2="7" stroke="rgba(244,240,229,.16)" strokeWidth="1.4" />
                </pattern>
              </defs>
              <rect x={-40} y={-40} width={box.W + 80} height={box.H + 80} rx={26} className={s.base} />
              {outline.map((pts, i) => (
                <polygon key={i} points={pts} className={s.land} />
              ))}
              {geo.grid.map((c) => {
                const [x, y] = box.px(c.lon - 0.3125, c.lat + 0.25);
                return (
                  <rect
                    key={c.id}
                    x={x}
                    y={y}
                    width={cw}
                    height={ch}
                    className={s.cellLine}
                    fill={c.weight > 0 ? 'none' : 'url(#hatch)'}
                  />
                );
              })}
              {MAP_PLACES.map((p) => {
                const [x, y] = box.px(p.lon, p.lat);
                return (
                  <g key={p.id} className={s.place}>
                    <circle cx={x} cy={y} r={3.2} />
                    <text x={x + 7} y={y + 4}>
                      {p.approx ? t.places.approx(t.places[p.name]) : t.places[p.name]}
                    </text>
                  </g>
                );
              })}
            </svg>
            {geo.grid
              .filter((c) => c.weight > 0)
              .map((c) => {
                const [x, y] = box.px(c.lon - 0.3125, c.lat + 0.25);
                const v = cellMagnitude(magKey, c.id, year);
                const met = cellMet(rule, c.id, year);
                const h = flat ? 0 : 6 + (v / magMax) * HMAX;
                const pad = 6,
                  w = cw - pad * 2,
                  d = ch - pad * 2;
                const top = met ? color : `color-mix(in srgb, ${color} 22%, #23382a)`;
                const side = (k: number) => `color-mix(in srgb, ${met ? color : '#5f7a66'} ${k}%, #050a06)`;
                return (
                  <button
                    key={c.id}
                    type="button"
                    className={[s.prism, selected === c.id ? s.sel : ''].join(' ')}
                    style={{ left: x + pad, top: y + pad, width: w, height: d }}
                    onClick={() => {
                      if (!drag.current?.moved) onSelect(c.id);
                    }}
                    aria-pressed={selected === c.id}
                    aria-label={`${t.science.cell} ${c.lat}°N ${c.lon}°E: ${f.n(v, 1)} ${RULES[rule].unit[lang]}, ${met ? t.science.met : t.science.notMet}`}
                  >
                    <span
                      className={s.face}
                      style={{
                        width: w,
                        height: h,
                        top: d,
                        transformOrigin: 'top',
                        transform: 'rotateX(90deg)',
                        background: side(70),
                      }}
                    />
                    <span
                      className={s.face}
                      style={{
                        width: h,
                        height: d,
                        left: w,
                        transformOrigin: 'left',
                        transform: 'rotateY(-90deg)',
                        background: side(55),
                      }}
                    />
                    <span
                      className={s.face}
                      style={{
                        width: w,
                        height: h,
                        top: -h,
                        transformOrigin: 'bottom',
                        transform: 'rotateX(-90deg)',
                        background: side(82),
                      }}
                    />
                    <span
                      className={s.face}
                      style={{
                        width: h,
                        height: d,
                        left: -h,
                        transformOrigin: 'right',
                        transform: 'rotateY(90deg)',
                        background: side(64),
                      }}
                    />
                    <span
                      className={`${s.face} ${s.top}`}
                      style={{
                        inset: 0,
                        transform: `translateZ(${h}px)`,
                        background: top,
                        opacity: 0.55 + 0.45 * Math.min(1, c.weight / 0.5),
                      }}
                    >
                      <span className={s.topLabel}>{f.n(v)}</span>
                    </span>
                  </button>
                );
              })}
          </div>
        </div>
        <p className={s.hint}>{flat ? t.science.flatHint : t.science.dragHint}</p>
      </div>
      <div className={s.legend}>
        <span>
          <i style={{ background: color }} />
          {t.science.met}
        </span>
        <span>
          <i style={{ background: `color-mix(in srgb, ${color} 22%, #23382a)` }} />
          {t.science.notMet}
        </span>
        <span>
          <i className={s.hatchKey} />
          {t.science.zeroWeight}
        </span>
        <span className="mono">
          {t.science.measured}: {RULES[rule].unit[lang]}
        </span>
      </div>
    </div>
  );
}
