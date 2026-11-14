import { useEffect, useMemo, useRef, useState } from 'react';
import {
  ACESFilmicToneMapping, BoxGeometry, BufferGeometry, CircleGeometry, Color, CylinderGeometry, DirectionalLight, EdgesGeometry,
  ExtrudeGeometry, Float32BufferAttribute, Fog, Group, HemisphereLight, Line, LineBasicMaterial, LineDashedMaterial,
  LineSegments, Mesh, MeshStandardMaterial, PCFSoftShadowMap, PerspectiveCamera, Raycaster, SRGBColorSpace, Scene, Shape,
  Spherical, Vector2, Vector3, WebGLRenderer, type Material, type Object3D,
} from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import { geo, hazards, type RuleCode } from '../../data';
import { cellMagnitude, cellMet, RULES } from '../../domain/hazards';
import { Icon } from '../../design-system/Icon';
import { useFormat, useSettings, useT } from '../../app/settings';
import { Grid3D } from './Grid3D';
import s from './Observatory3D.module.css';

// Real geometry only: the geoBoundaries outline of Nghệ An and the NASA POWER cells at their true centres, in an
// equirectangular projection scaled by cos(latitude) so a degree of longitude keeps its real ground length.
const S = 10; // scene units per degree of latitude
const K_LON = Math.cos((19.3 * Math.PI) / 180);
const HALF_LAT = 0.25, HALF_LON = 0.3125; // POWER cell half sizes in degrees
const HMAX = 6.5; // column height for the largest value of the chosen measure, in scene units
const PLACES = [
  { id: 'vinh', lat: 18.68, lon: 105.68, vi: '≈ TP Vinh', en: '≈ Vinh city' },
  { id: 'doluong', lat: 18.9, lon: 105.3, vi: '≈ Đô Lương · nơi thử nghiệm', en: '≈ Đô Lương · trial site' },
];

const [minLon, minLat, maxLon, maxLat] = geo.bounds;
const LON0 = (minLon + maxLon) / 2, LAT0 = (minLat + maxLat) / 2;
const toX = (lon: number) => (lon - LON0) * K_LON * S;
const toZ = (lat: number) => -(lat - LAT0) * S;

function hasWebGL(): boolean {
  try {
    const c = document.createElement('canvas');
    return !!(c.getContext('webgl2') ?? c.getContext('webgl'));
  } catch {
    return false;
  }
}

/** Reads a CSS colour token (e.g. "var(--data-heat)") from an element so the scene uses the design tokens. */
function cssColor(el: Element, token: string): Color {
  const name = /var\((--[\w-]+)\)/.exec(token)?.[1];
  const raw = name ? getComputedStyle(el).getPropertyValue(name).trim() : token;
  try {
    return new Color(raw || '#e9bc57');
  } catch {
    return new Color('#e9bc57');
  }
}

interface Column {
  id: string;
  mesh: Mesh<BoxGeometry, MeshStandardMaterial>;
  edges: LineSegments;
  from: number;
  to: number;
}

interface Stage {
  setData: (rule: RuleCode, year: number, animate: boolean) => void;
  setSelected: (id: string) => void;
  orbit: (dTheta: number, dPhi: number) => void;
  reset: () => void;
}

/**
 * The flagship observatory: a WebGL scene of real Nghệ An geometry. Loaded only by the science page (code split),
 * rendered on demand (never a perpetual loop), disposed on unmount; 2D in lite mode, under reduced motion or
 * without WebGL (UI-UX-SPEC H1, D-155).
 */
export function Observatory3D({ rule, year, selected, onSelect }: { rule: RuleCode; year: number; selected: string; onSelect: (id: string) => void }) {
  const t = useT();
  const f = useFormat();
  const { calm, lang } = useSettings();
  const [want3d, setWant3d] = useState(true);
  const [failed, setFailed] = useState(false);
  const supported = useMemo(() => typeof window !== 'undefined' && hasWebGL(), []);
  const show3d = want3d && !calm && supported && !failed;

  const host = useRef<HTMLDivElement>(null);
  const labels = useRef<HTMLDivElement>(null);
  const stage = useRef<Stage | null>(null);
  const selectRef = useRef(onSelect);
  selectRef.current = onSelect;

  const magKey = RULES[rule].magnitude;
  const magMax = useMemo(() => Math.max(1, ...Object.values(hazards.magnitudes[magKey]).flat()), [magKey]);
  const weighted = useMemo(() => geo.grid.filter((c) => c.weight > 0), []);

  useEffect(() => {
    if (!show3d) return;
    const el = host.current;
    const overlay = labels.current;
    if (!el || !overlay) return;

    let renderer: WebGLRenderer;
    try {
      renderer = new WebGLRenderer({ antialias: true, alpha: false, powerPreference: 'high-performance' });
    } catch {
      setFailed(true);
      return;
    }
    const small = el.clientWidth < 640;
    renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, small ? 1.5 : 2));
    renderer.outputColorSpace = SRGBColorSpace;
    renderer.toneMapping = ACESFilmicToneMapping;
    renderer.toneMappingExposure = 1.05;
    renderer.shadowMap.enabled = !small;
    renderer.shadowMap.type = PCFSoftShadowMap;
    renderer.domElement.setAttribute('aria-hidden', 'true');
    renderer.domElement.className = s.canvas ?? '';
    el.prepend(renderer.domElement);

    const scene = new Scene();
    const bg = new Color('#0b1a10');
    scene.background = bg;
    scene.fog = new Fog(bg, 48, 120);

    const camera = new PerspectiveCamera(36, 1, 0.5, 400);
    const controls = new OrbitControls(camera, renderer.domElement);
    controls.enableDamping = true;
    controls.dampingFactor = 0.085;
    controls.enablePan = false;
    controls.minPolarAngle = 0.2;
    controls.maxPolarAngle = 1.32;
    controls.minDistance = 22;
    controls.maxDistance = 85;
    controls.rotateSpeed = 0.6;
    controls.target.set(0.6, 0.6, 0.4);
    const startDir = new Spherical(small ? 60 : 50, 0.9, -0.38);
    camera.position.setFromSpherical(startDir).add(controls.target);
    controls.update();
    controls.saveState();

    // light: warm low sun from the south-west, sky and paddy bounce
    scene.add(new HemisphereLight('#f4e6c4', '#1d3a25', 0.95));
    const sun = new DirectionalLight('#ffd89a', 2.1);
    sun.position.set(-26, 34, 22);
    sun.castShadow = !small;
    sun.shadow.mapSize.set(1024, 1024);
    sun.shadow.camera.left = -26; sun.shadow.camera.right = 26; sun.shadow.camera.top = 26; sun.shadow.camera.bottom = -26;
    sun.shadow.bias = -0.0008;
    scene.add(sun);

    const world = new Group();
    scene.add(world);

    // ground disc
    const ground = new Mesh(new CircleGeometry(80, 64), new MeshStandardMaterial({ color: '#10261a', roughness: 1 }));
    ground.rotation.x = -Math.PI / 2;
    ground.position.y = -0.02;
    ground.receiveShadow = true;
    world.add(ground);

    // province, extruded from the real outline
    for (const ring of geo.outline) {
      const shape = new Shape(ring.map(([lon, lat]) => new Vector2(toX(lon), (lat - LAT0) * S)));
      const land = new Mesh(
        new ExtrudeGeometry(shape, { depth: 0.32, bevelEnabled: true, bevelSize: 0.06, bevelThickness: 0.06, bevelSegments: 2 }),
        new MeshStandardMaterial({ color: '#2f5a37', roughness: 0.92, metalness: 0 }),
      );
      land.rotation.x = -Math.PI / 2;
      land.receiveShadow = true;
      world.add(land);
      const pts = ring.map(([lon, lat]) => new Vector3(toX(lon), 0.42, toZ(lat)));
      world.add(new Line(new BufferGeometry().setFromPoints(pts), new LineBasicMaterial({ color: '#f2d590', transparent: true, opacity: 0.9 })));
    }

    // POWER cell footprints (dashed); cells without farmland weight stay dim
    for (const c of geo.grid) {
      const x0 = toX(c.lon - HALF_LON), x1 = toX(c.lon + HALF_LON), z0 = toZ(c.lat + HALF_LAT), z1 = toZ(c.lat - HALF_LAT);
      const y = 0.45;
      const g = new BufferGeometry();
      g.setAttribute('position', new Float32BufferAttribute([x0, y, z0, x1, y, z0, x1, y, z1, x0, y, z1, x0, y, z0], 3));
      const line = new Line(g, new LineDashedMaterial({ color: '#f4f0e5', dashSize: 0.35, gapSize: 0.3, transparent: true, opacity: c.weight > 0 ? 0.42 : 0.16 }));
      line.computeLineDistances();
      world.add(line);
    }

    // data columns for the farmland-weighted cells
    const columns = new Map<string, Column>();
    const cw = 2 * HALF_LON * K_LON * S * 0.5, cd = 2 * HALF_LAT * S * 0.5;
    for (const c of weighted) {
      const geom = new BoxGeometry(cw, 1, cd);
      geom.translate(0, 0.5, 0);
      const mat = new MeshStandardMaterial({ color: '#7d9a6b', roughness: 0.55, metalness: 0.05, transparent: true, opacity: 0.94 });
      const mesh = new Mesh(geom, mat);
      mesh.position.set(toX(c.lon), 0.42, toZ(c.lat));
      mesh.scale.y = 0.001;
      mesh.castShadow = true;
      mesh.receiveShadow = true;
      mesh.userData.cellId = c.id;
      const edges = new LineSegments(new EdgesGeometry(geom), new LineBasicMaterial({ color: '#f2d590' }));
      edges.visible = false;
      mesh.add(edges);
      world.add(mesh);
      columns.set(c.id, { id: c.id, mesh, edges, from: 0.001, to: 0.001 });
    }

    // the trial site and Vinh as thin pins
    for (const p of PLACES) {
      const pin = new Mesh(new CylinderGeometry(0.06, 0.06, 2.4, 8), new MeshStandardMaterial({ color: p.id === 'doluong' ? '#e9bc57' : '#f4f0e5', emissive: p.id === 'doluong' ? '#5a3d07' : '#000000' }));
      pin.position.set(toX(p.lon), 1.6, toZ(p.lat));
      world.add(pin);
    }

    // ---- render on demand ----
    let raf = 0;
    let tweenStart = 0;
    let tweenMs = 0;
    const ease = (k: number) => 1 - Math.pow(1 - k, 3);
    const v3 = new Vector3();
    const placeLabels = () => {
      const w = el.clientWidth, h = el.clientHeight;
      for (const node of Array.from(overlay.children) as HTMLElement[]) {
        const id = node.dataset.id;
        const col = id ? columns.get(id) : undefined;
        if (col) v3.set(col.mesh.position.x, col.mesh.position.y + col.mesh.scale.y + 0.6, col.mesh.position.z);
        else {
          const p = PLACES.find((q) => q.id === node.dataset.place);
          if (!p) continue;
          v3.set(toX(p.lon), 3.1, toZ(p.lat));
        }
        v3.project(camera);
        const hidden = v3.z > 1;
        node.style.transform = `translate(-50%, -100%) translate(${((v3.x + 1) / 2) * w}px, ${((1 - v3.y) / 2) * h}px)`;
        node.style.visibility = hidden ? 'hidden' : 'visible';
      }
    };
    const frame = (now: number) => {
      raf = 0;
      const moving = controls.update();
      let tweening = false;
      if (tweenMs > 0) {
        const k = Math.min(1, (now - tweenStart) / tweenMs);
        for (const c of columns.values()) c.mesh.scale.y = c.from + (c.to - c.from) * ease(k);
        tweening = k < 1;
        if (!tweening) tweenMs = 0;
      }
      renderer.render(scene, camera);
      placeLabels();
      if (moving || tweening) raf = requestAnimationFrame(frame);
    };
    const request = () => { if (!raf) raf = requestAnimationFrame(frame); };
    controls.addEventListener('change', request);

    const resize = () => {
      const w = el.clientWidth, h = el.clientHeight;
      if (!w || !h) return;
      renderer.setSize(w, h, false);
      camera.aspect = w / h;
      camera.updateProjectionMatrix();
      request();
    };
    const ro = new ResizeObserver(resize);
    ro.observe(el);
    resize();

    // ---- picking: a tap (not a drag) on a column selects its cell ----
    const ray = new Raycaster();
    const ndc = new Vector2();
    let down: { x: number; y: number } | null = null;
    const meshes = [...columns.values()].map((c) => c.mesh);
    const hit = (e: PointerEvent) => {
      const r = renderer.domElement.getBoundingClientRect();
      ndc.set(((e.clientX - r.left) / r.width) * 2 - 1, -((e.clientY - r.top) / r.height) * 2 + 1);
      ray.setFromCamera(ndc, camera);
      return ray.intersectObjects(meshes, false)[0]?.object.userData.cellId as string | undefined;
    };
    const onDown = (e: PointerEvent) => { down = { x: e.clientX, y: e.clientY }; };
    const onUp = (e: PointerEvent) => {
      if (down && Math.hypot(e.clientX - down.x, e.clientY - down.y) < 6) {
        const id = hit(e);
        if (id) selectRef.current(id);
      }
      down = null;
    };
    const onMove = (e: PointerEvent) => { if (!down) renderer.domElement.style.cursor = hit(e) ? 'pointer' : 'grab'; };
    renderer.domElement.addEventListener('pointerdown', onDown);
    renderer.domElement.addEventListener('pointerup', onUp);
    renderer.domElement.addEventListener('pointermove', onMove);

    const offset = new Vector3();
    const sph = new Spherical();
    stage.current = {
      setData: (r, yr, animate) => {
        const key = RULES[r].magnitude;
        const max = Math.max(1, ...Object.values(hazards.magnitudes[key]).flat());
        const on = cssColor(el, RULES[r].color);
        const off = on.clone().lerp(new Color('#3c5a43'), 0.72);
        for (const c of columns.values()) {
          const v = cellMagnitude(key, c.id, yr);
          const met = cellMet(r, c.id, yr);
          c.from = c.mesh.scale.y;
          c.to = 0.25 + (v / max) * HMAX;
          c.mesh.material.color.copy(met ? on : off);
          c.mesh.material.emissive.copy(met ? on : off).multiplyScalar(met ? 0.16 : 0.02);
          if (!animate) c.mesh.scale.y = c.to;
        }
        tweenStart = performance.now();
        tweenMs = animate ? 640 : 0;
        request();
      },
      setSelected: (id) => {
        for (const c of columns.values()) c.edges.visible = c.id === id;
        request();
      },
      orbit: (dTheta, dPhi) => {
        offset.copy(camera.position).sub(controls.target);
        sph.setFromVector3(offset);
        sph.theta += dTheta;
        sph.phi = Math.min(controls.maxPolarAngle, Math.max(controls.minPolarAngle, sph.phi + dPhi));
        camera.position.setFromSpherical(sph).add(controls.target);
        request();
      },
      reset: () => { controls.reset(); request(); },
    };

    return () => {
      cancelAnimationFrame(raf);
      ro.disconnect();
      controls.removeEventListener('change', request);
      controls.dispose();
      renderer.domElement.removeEventListener('pointerdown', onDown);
      renderer.domElement.removeEventListener('pointerup', onUp);
      renderer.domElement.removeEventListener('pointermove', onMove);
      scene.traverse((o: Object3D) => {
        const m = o as Mesh;
        m.geometry?.dispose();
        const mat = m.material as Material | Material[] | undefined;
        if (Array.isArray(mat)) mat.forEach((x) => x.dispose()); else mat?.dispose();
      });
      renderer.dispose();
      renderer.domElement.remove();
      stage.current = null;
    };
  }, [show3d, weighted]);

  const first = useRef(true);
  useEffect(() => {
    stage.current?.setData(rule, year, !first.current);
    first.current = false;
  }, [rule, year, show3d]);
  useEffect(() => { stage.current?.setSelected(selected); }, [selected, show3d]);

  if (!show3d) {
    return (
      <div className={s.flatWrap}>
        <Grid3D rule={rule} year={year} selected={selected} onSelect={onSelect} forceFlat />
        {!calm && supported && !failed && (
          <button type="button" className={s.switchBack} onClick={() => setWant3d(true)}>{t.science.view3d}</button>
        )}
        {(failed || !supported) && <p className={s.note}>{t.science.noWebgl}</p>}
      </div>
    );
  }

  const color = RULES[rule].color;
  return (
    <div className={s.wrap}>
      <div
        ref={host} className={s.stage} tabIndex={0} role="group"
        aria-label={`${t.science.mapTitle}. ${t.science.dragHint}`}
        onKeyDown={(e) => {
          const step = { ArrowLeft: [-0.18, 0], ArrowRight: [0.18, 0], ArrowUp: [0, -0.08], ArrowDown: [0, 0.08] }[e.key];
          if (!step) return;
          e.preventDefault();
          stage.current?.orbit(step[0] ?? 0, step[1] ?? 0);
        }}
      >
        <div ref={labels} className={s.labels} aria-hidden="true">
          {weighted.map((c) => (
            <span key={c.id} data-id={c.id} className={[s.value, c.id === selected ? s.valueSel : ''].join(' ')}>
              {f.n(cellMagnitude(magKey, c.id, year))}
            </span>
          ))}
          {PLACES.map((p) => <span key={p.id} data-place={p.id} className={s.place}>{lang === 'vi' ? p.vi : p.en}</span>)}
        </div>
        <div className={s.controls}>
          <button type="button" onClick={() => stage.current?.orbit(-0.5, 0)} aria-label={t.science.rotateLeft}><Icon name="rotateL" size={20} /></button>
          <button type="button" onClick={() => stage.current?.orbit(0.5, 0)} aria-label={t.science.rotateRight}><Icon name="rotateR" size={20} /></button>
          <button type="button" onClick={() => stage.current?.reset()} aria-label={t.science.reset}><Icon name="reset" size={20} /></button>
          <button type="button" className={s.mode} onClick={() => setWant3d(false)}>{t.science.view2d}</button>
        </div>
        <p className={s.badge}><span className={s.dot} aria-hidden="true" />{t.science.realGeometryShort}</p>
        <p className={s.hint}>{t.science.dragHint}</p>
      </div>
      <div className={s.legend}>
        <span><i style={{ background: color }} />{t.science.met}</span>
        <span><i style={{ background: `color-mix(in srgb, ${color} 28%, #3c5a43)` }} />{t.science.notMet}</span>
        <span><i className={s.dash} />{t.science.cellFootprint}</span>
        <span>{t.science.realGeometry}</span>
        <span className="mono">{t.science.heightIs}: {RULES[rule].unit[lang]} · max {f.n(magMax)}</span>
      </div>
    </div>
  );
}
