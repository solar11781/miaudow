import {
  ACESFilmicToneMapping, BoxGeometry, BufferGeometry, CircleGeometry, Color, CylinderGeometry, DirectionalLight, EdgesGeometry,
  ExtrudeGeometry, Float32BufferAttribute, Fog, Group, HemisphereLight, Line, LineBasicMaterial, LineDashedMaterial,
  LineSegments, Mesh, MeshStandardMaterial, PCFSoftShadowMap, PerspectiveCamera, Raycaster, SRGBColorSpace, Scene, Shape,
  Spherical, Vector2, Vector3, WebGLRenderer, type Material, type Object3D,
} from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import { geo, hazards, type RuleCode } from '../../data';
import { cellMagnitude, cellMet, RULES } from '../../domain/hazards';

// Real geometry only: the geoBoundaries outline of Nghệ An and the NASA POWER cells at their true centres, in an
// equirectangular projection scaled by cos(latitude) so a degree of longitude keeps its real ground length.
export const S = 10; // scene units per degree of latitude
const K_LON = Math.cos((19.3 * Math.PI) / 180);
const HALF_LAT = 0.25, HALF_LON = 0.3125; // POWER cell half sizes in degrees
const HMAX = 6.5; // column height for the largest value of the chosen measure, in scene units
// The trial commune's map marker (Wikidata Q10788283) and Vinh, for orientation only.
export const PLACES = [
  { id: 'vinh', lat: 18.68, lon: 105.68, vi: 'TP Vinh', en: 'Vinh city' },
  { id: 'doluong', lat: 18.8964, lon: 105.2803, vi: 'Lưu Sơn · nơi thử nghiệm', en: 'Lưu Sơn · trial site' },
];
export const WEIGHTED = geo.grid.filter((c) => c.weight > 0);

const [minLon, minLat, maxLon, maxLat] = geo.bounds;
const LON0 = (minLon + maxLon) / 2, LAT0 = (minLat + maxLat) / 2;
const toX = (lon: number) => (lon - LON0) * K_LON * S;
const toZ = (lat: number) => -(lat - LAT0) * S;

export function hasWebGL(): boolean {
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

export interface Observatory {
  setData: (rule: RuleCode, year: number, animate: boolean) => void;
  setSelected: (id: string) => void;
  orbit: (dTheta: number, dPhi: number) => void;
  reset: () => void;
  dispose: () => void;
}

function makeRenderer(el: HTMLElement, className: string): { renderer: WebGLRenderer; small: boolean } | null {
  let renderer: WebGLRenderer;
  try {
    renderer = new WebGLRenderer({ antialias: true, alpha: false, powerPreference: 'high-performance' });
  } catch {
    return null;
  }
  const small = el.clientWidth < 640;
  renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, small ? 1.5 : 2));
  renderer.outputColorSpace = SRGBColorSpace;
  renderer.toneMapping = ACESFilmicToneMapping;
  renderer.toneMappingExposure = 1.05;
  renderer.shadowMap.enabled = !small;
  renderer.shadowMap.type = PCFSoftShadowMap;
  renderer.domElement.setAttribute('aria-hidden', 'true');
  renderer.domElement.className = className;
  el.prepend(renderer.domElement);
  return { renderer, small };
}

function makeCamera(renderer: WebGLRenderer, small: boolean) {
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
  camera.position.setFromSpherical(new Spherical(small ? 60 : 50, 0.9, -0.38)).add(controls.target);
  controls.update();
  controls.saveState();
  return { camera, controls };
}

/** Warm low sun from the south-west, sky and paddy bounce. */
function addLights(scene: Scene, small: boolean) {
  scene.add(new HemisphereLight('#f4e6c4', '#1d3a25', 0.95));
  const sun = new DirectionalLight('#ffd89a', 2.1);
  sun.position.set(-26, 34, 22);
  sun.castShadow = !small;
  sun.shadow.mapSize.set(1024, 1024);
  Object.assign(sun.shadow.camera, { left: -26, right: 26, top: 26, bottom: -26 });
  sun.shadow.bias = -0.0008;
  scene.add(sun);
}

function addLand(world: Group) {
  const ground = new Mesh(new CircleGeometry(80, 64), new MeshStandardMaterial({ color: '#10261a', roughness: 1 }));
  ground.rotation.x = -Math.PI / 2;
  ground.position.y = -0.02;
  ground.receiveShadow = true;
  world.add(ground);
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
}

/** POWER cell footprints (dashed); cells without farmland weight stay dim. */
function addFootprints(world: Group) {
  for (const c of geo.grid) {
    const x0 = toX(c.lon - HALF_LON), x1 = toX(c.lon + HALF_LON), z0 = toZ(c.lat + HALF_LAT), z1 = toZ(c.lat - HALF_LAT);
    const y = 0.45;
    const g = new BufferGeometry();
    g.setAttribute('position', new Float32BufferAttribute([x0, y, z0, x1, y, z0, x1, y, z1, x0, y, z1, x0, y, z0], 3));
    const line = new Line(g, new LineDashedMaterial({ color: '#f4f0e5', dashSize: 0.35, gapSize: 0.3, transparent: true, opacity: c.weight > 0 ? 0.42 : 0.16 }));
    line.computeLineDistances();
    world.add(line);
  }
}

function addColumns(world: Group): Map<string, Column> {
  const columns = new Map<string, Column>();
  const cw = 2 * HALF_LON * K_LON * S * 0.5, cd = 2 * HALF_LAT * S * 0.5;
  for (const c of WEIGHTED) {
    const geom = new BoxGeometry(cw, 1, cd);
    geom.translate(0, 0.5, 0);
    const mesh = new Mesh(geom, new MeshStandardMaterial({ color: '#7d9a6b', roughness: 0.55, metalness: 0.05, transparent: true, opacity: 0.94 }));
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
  for (const p of PLACES) {
    const site = p.id === 'doluong';
    const pin = new Mesh(new CylinderGeometry(0.06, 0.06, 2.4, 8), new MeshStandardMaterial({ color: site ? '#e9bc57' : '#f4f0e5', emissive: site ? '#5a3d07' : '#000000' }));
    pin.position.set(toX(p.lon), 1.6, toZ(p.lat));
    world.add(pin);
  }
  return columns;
}

/** Positions the HTML labels (values and places) over the columns and pins after each render. */
function placeLabels(el: HTMLElement, overlay: HTMLElement, columns: Map<string, Column>, camera: PerspectiveCamera, v3: Vector3) {
  const w = el.clientWidth, h = el.clientHeight;
  for (const node of Array.from(overlay.children) as HTMLElement[]) {
    const col = node.dataset.id ? columns.get(node.dataset.id) : undefined;
    const place = PLACES.find((q) => q.id === node.dataset.place);
    if (col) v3.set(col.mesh.position.x, col.mesh.position.y + col.mesh.scale.y + 0.6, col.mesh.position.z);
    else if (place) v3.set(toX(place.lon), 2.8, toZ(place.lat));
    else continue;
    v3.project(camera);
    // values sit above their column; place names sit beside their pin (the trial site to the left, Vinh to the right)
    const shift = col ? 'translate(-50%, -100%)' : place?.id === 'doluong' ? 'translate(calc(-100% - 10px), -50%)' : 'translate(10px, -50%)';
    node.style.transform = `${shift} translate(${((v3.x + 1) / 2) * w}px, ${((1 - v3.y) / 2) * h}px)`;
    node.style.visibility = v3.z > 1 ? 'hidden' : 'visible';
  }
}

function disposeScene(scene: Scene) {
  scene.traverse((o: Object3D) => {
    const m = o as Mesh;
    m.geometry?.dispose();
    const mat = m.material as Material | Material[] | undefined;
    if (Array.isArray(mat)) mat.forEach((x) => x.dispose()); else mat?.dispose();
  });
}

/**
 * Builds the scene into `el` and returns its controls, or null when WebGL cannot start. Renders on demand only:
 * a frame is drawn while the camera moves or a column grows, never in a perpetual loop.
 */
export function createObservatory(el: HTMLElement, overlay: HTMLElement, canvasClass: string, onPick: (id: string) => void): Observatory | null {
  const made = makeRenderer(el, canvasClass);
  if (!made) return null;
  const { renderer, small } = made;
  const scene = new Scene();
  const bg = new Color('#0b1a10');
  scene.background = bg;
  scene.fog = new Fog(bg, 48, 120);
  const { camera, controls } = makeCamera(renderer, small);
  addLights(scene, small);
  const world = new Group();
  scene.add(world);
  addLand(world);
  addFootprints(world);
  const columns = addColumns(world);

  let raf = 0, tweenStart = 0, tweenMs = 0;
  const ease = (k: number) => 1 - Math.pow(1 - k, 3);
  const v3 = new Vector3();
  const frame = (now: number) => {
    raf = 0;
    const moving = controls.update();
    const k = tweenMs > 0 ? Math.min(1, (now - tweenStart) / tweenMs) : 1;
    if (tweenMs > 0) for (const c of columns.values()) c.mesh.scale.y = c.from + (c.to - c.from) * ease(k);
    if (k >= 1) tweenMs = 0;
    renderer.render(scene, camera);
    placeLabels(el, overlay, columns, camera, v3);
    if (moving || tweenMs > 0) raf = requestAnimationFrame(frame);
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

  // picking: a tap (not a drag) on a column selects its cell
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
    const id = down && Math.hypot(e.clientX - down.x, e.clientY - down.y) < 6 ? hit(e) : undefined;
    if (id) onPick(id);
    down = null;
  };
  const onMove = (e: PointerEvent) => { if (!down) renderer.domElement.style.cursor = hit(e) ? 'pointer' : 'grab'; };
  renderer.domElement.addEventListener('pointerdown', onDown);
  renderer.domElement.addEventListener('pointerup', onUp);
  renderer.domElement.addEventListener('pointermove', onMove);

  const offset = new Vector3();
  const sph = new Spherical();
  return {
    setData: (rule, year, animate) => {
      const key = RULES[rule].magnitude;
      const max = Math.max(1, ...Object.values(hazards.magnitudes[key]).flat());
      const on = cssColor(el, RULES[rule].color);
      const off = on.clone().lerp(new Color('#3c5a43'), 0.72);
      for (const c of columns.values()) {
        const met = cellMet(rule, c.id, year);
        c.from = c.mesh.scale.y;
        c.to = 0.25 + (cellMagnitude(key, c.id, year) / max) * HMAX;
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
    dispose: () => {
      cancelAnimationFrame(raf);
      ro.disconnect();
      controls.removeEventListener('change', request);
      controls.dispose();
      renderer.domElement.removeEventListener('pointerdown', onDown);
      renderer.domElement.removeEventListener('pointerup', onUp);
      renderer.domElement.removeEventListener('pointermove', onMove);
      disposeScene(scene);
      renderer.dispose();
      renderer.domElement.remove();
    },
  };
}
