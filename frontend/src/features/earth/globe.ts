// The Earth observatory's globe (CesiumJS, WGS84). Loaded only by the observatory page. Nothing here invents a value:
// geometry comes from geoBoundaries, the cells and their numbers from the canonical climate file, imagery from NASA
// GIBS (a visual source, labelled as such) and the Sentinel-2 composites from the team's processing.
import {
  Cartesian2,
  Cartesian3,
  CallbackProperty,
  Color,
  ColorMaterialProperty,
  EllipsoidTerrainProvider,
  HorizontalOrigin,
  ImageryLayer,
  JulianDate,
  LabelStyle,
  Math as CMath,
  NearFarScalar,
  Rectangle,
  ScreenSpaceEventHandler,
  ScreenSpaceEventType,
  SingleTileImageryProvider,
  UrlTemplateImageryProvider,
  VerticalOrigin,
  Viewer,
  type Entity,
} from 'cesium';
import { geo } from '../../data';
import { TRIAL_SITE } from '../../data/places';
import { en } from '../../i18n/en';
import { vi } from '../../i18n/vi';
import { cellYear } from './cellClimate';
import { FLAGSHIPS, satelliteImage, trackFrame, trackPoint, wrap } from './flagships';
import { MISSIONS } from './missions';
import { SCENES, type SceneId } from './scenes';
import doLuongJson from '@data/geo_do_luong.json';
import vegetationJson from '@data/vegetation.json';

export type Overlay = 'none' | 'ndvi-modis' | 'imerg' | 'smap' | 's2';

interface Composite {
  id: string;
  season: string;
  year: number;
  png: string;
  bounds: [number, number, number, number];
}
const DO_LUONG = doLuongJson as unknown as { do_luong: { outline: [number, number][][] } };
const VEG = vegetationJson as unknown as { composites: Composite[] };

const GIBS = 'https://gibs.earthdata.nasa.gov/wmts/epsg3857/best';
const gibs = (layer: string, matrix: string, ext: 'jpeg' | 'png', time?: string) =>
  new UrlTemplateImageryProvider({
    url: `${GIBS}/${layer}/default/${time ? `${time}/` : ''}${matrix}/{z}/{y}/{x}.${ext}`,
    maximumLevel: Number(matrix.replace(/\D+/g, '')),
    credit: 'NASA GIBS',
  });

/** Reference places for orientation (city centres, rounded; the district label sits inside the geoBoundaries outline). */
const PLACES = [
  { vi: vi.places.vietnam, en: en.places.vietnam, lat: 14.2, lon: 108.2, big: true, dot: false, near: 1.5e6, far: 6e6 },
  // Vietnam's islands, shown wherever the country is (member A); points from Wikidata Q274388, Q215664, Q146695
  {
    vi: vi.places.hoangSa,
    en: en.places.hoangSa,
    lat: 16.654612,
    lon: 112.747192,
    big: false,
    dot: true,
    near: 1e5,
    far: 9e6,
  },
  { vi: vi.places.truongSa, en: en.places.truongSa, lat: 10, lon: 114, big: false, dot: true, near: 1e5, far: 9e6 },
  {
    vi: vi.places.phuQuoc,
    en: en.places.phuQuoc,
    lat: 10.228889,
    lon: 103.957222,
    big: false,
    dot: true,
    near: 1e5,
    far: 9e6,
  },
  { vi: vi.places.hanoi, en: en.places.hanoi, lat: 21.03, lon: 105.85, big: false, dot: true, near: 4e5, far: 9e6 },
  { vi: vi.places.vinh, en: en.places.vinh, lat: 18.68, lon: 105.69, big: false, dot: true, near: 5e4, far: 1.5e6 },
  { vi: vi.places.ngheAn, en: en.places.ngheAn, lat: 19.25, lon: 104.75, big: true, dot: false, near: 1e5, far: 1.6e6 },
  {
    vi: vi.places.formerDoLuong,
    en: en.places.formerDoLuong,
    lat: 18.98,
    lon: 105.33,
    big: false,
    dot: false,
    near: 4e4,
    far: 1.4e5,
  },
];

/** Column height: metres of column per millimetre of annual rain (2,000 mm stands 28 km tall). For comparison only. */
const COLUMN_M_PER_MM = 14;
const DRY = Color.fromCssColorString('#b8861b');
const WET = Color.fromCssColorString('#2e6f9b');
const MID = Color.fromCssColorString('#c9d1c6');
function anomalyColor(a: number): Color {
  const k = Math.min(1, Math.abs(a) / 0.35);
  return Color.lerp(MID, a < 0 ? DRY : WET, k, new Color()).withAlpha(0.88);
}

/** Positions of a circular orbit ring (illustrative: fixed in the Earth frame, nominal height and inclination). */
function orbitPoint(altKm: number, incDeg: number, raanDeg: number, theta: number): Cartesian3 {
  const r = 6_371_000 + altKm * 1000;
  const i = CMath.toRadians(incDeg),
    o = CMath.toRadians(raanDeg);
  const x = r * Math.cos(theta),
    y = r * Math.sin(theta);
  const y1 = y * Math.cos(i),
    z1 = y * Math.sin(i);
  return new Cartesian3(x * Math.cos(o) - y1 * Math.sin(o), x * Math.sin(o) + y1 * Math.cos(o), z1);
}

export interface Globe {
  goTo: (scene: SceneId, instant: boolean) => void;
  setYear: (year: number) => void;
  setOverlay: (overlay: Overlay, year: number, composite: string) => void;
  setSelected: (cell: string) => void;
  setOrbits: (on: boolean, moving: boolean) => void;
  /** The two flagship satellites over Nghệ An (illustrative orbits, scan beams over the province). */
  setFlagships: (on: boolean, moving: boolean) => void;
  stopFlight: () => void;
  dispose: () => void;
}

export function createGlobe(
  el: HTMLElement,
  creditEl: HTMLElement,
  onPick: (cell: string) => void,
  lang: 'vi' | 'en',
): Globe {
  const t = lang === 'vi' ? vi : en;
  const viewer = new Viewer(el, {
    baseLayer: new ImageryLayer(gibs('BlueMarble_NextGeneration', 'GoogleMapsCompatible_Level8', 'jpeg')),
    terrainProvider: new EllipsoidTerrainProvider(),
    animation: false,
    timeline: false,
    baseLayerPicker: false,
    geocoder: false,
    homeButton: false,
    sceneModePicker: false,
    navigationHelpButton: false,
    fullscreenButton: false,
    infoBox: false,
    selectionIndicator: false,
    creditContainer: creditEl,
    requestRenderMode: true,
    maximumRenderTimeChange: Infinity,
  });
  const scene = viewer.scene;
  scene.globe.enableLighting = true;
  scene.globe.baseColor = Color.fromCssColorString('#0b1a10');
  scene.backgroundColor = Color.fromCssColorString('#04070a');
  // late morning over Viet Nam on the June solstice: a lit Indochina with a visible day-night line to the east
  viewer.clock.currentTime = JulianDate.fromIso8601('2020-06-21T03:30:00Z');
  viewer.clock.shouldAnimate = false;
  // Place names are drawn here rather than taken from GIBS Reference_Labels_15m: that layer answers HTTP 500 for many
  // tiles over Viet Nam, and Cesium then paints those globe tiles black.
  const placeLabels = PLACES.map((p) =>
    viewer.entities.add({
      show: false,
      position: Cartesian3.fromDegrees(p.lon, p.lat, 300),
      point: p.dot
        ? {
            pixelSize: 7,
            color: Color.fromCssColorString('#f4f0e5'),
            outlineColor: Color.BLACK,
            outlineWidth: 1.5,
            disableDepthTestDistance: Number.POSITIVE_INFINITY,
          }
        : undefined,
      label: {
        text: lang === 'vi' ? p.vi : p.en,
        font: p.big ? '800 24px "Alegreya Variable", Georgia, serif' : '600 17px "Be Vietnam Pro", sans-serif',
        fillColor: Color.fromCssColorString(p.big ? '#f2d590' : '#f4f0e5'),
        outlineColor: Color.BLACK,
        outlineWidth: 3,
        style: LabelStyle.FILL_AND_OUTLINE,
        pixelOffset: new Cartesian2(p.dot ? 10 : 0, 0),
        horizontalOrigin: p.dot ? HorizontalOrigin.LEFT : HorizontalOrigin.CENTER,
        verticalOrigin: VerticalOrigin.CENTER,
        disableDepthTestDistance: Number.POSITIVE_INFINITY,
        translucencyByDistance: new NearFarScalar(p.near, 1, p.far, 0),
      },
    }),
  );

  // ---- Nghệ An and Đô Lương outlines (geoBoundaries) ----
  const ring = (pts: [number, number][]) => Cartesian3.fromDegreesArray(pts.flat());
  for (const r of geo.outline) {
    viewer.entities.add({
      polyline: { positions: ring(r), width: 2.5, material: Color.fromCssColorString('#f2d590') },
    });
  }
  for (const r of DO_LUONG.do_luong.outline) {
    viewer.entities.add({
      polygon: { hierarchy: ring(r), material: Color.fromCssColorString('#e9bc57').withAlpha(0.12), height: 0 },
      polyline: { positions: ring(r), width: 2, material: Color.fromCssColorString('#ffffff').withAlpha(0.85) },
    });
  }
  viewer.entities.add({
    position: Cartesian3.fromDegrees(TRIAL_SITE.lon, TRIAL_SITE.lat, 200),
    point: {
      pixelSize: 10,
      color: Color.fromCssColorString('#e9bc57'),
      outlineColor: Color.BLACK,
      outlineWidth: 2,
      disableDepthTestDistance: Number.POSITIVE_INFINITY,
    },
    label: {
      text: t.places.trialSite,
      font: '600 17px "Be Vietnam Pro", sans-serif',
      fillColor: Color.WHITE,
      outlineColor: Color.BLACK,
      outlineWidth: 3,
      style: LabelStyle.FILL_AND_OUTLINE,
      pixelOffset: new Cartesian2(14, 0),
      horizontalOrigin: HorizontalOrigin.LEFT,
      verticalOrigin: VerticalOrigin.CENTER,
      disableDepthTestDistance: Number.POSITIVE_INFINITY,
      translucencyByDistance: new NearFarScalar(2e5, 1, 9e5, 0),
    },
  });

  // ---- the five farmland cells: height = annual rain, colour = against the 1991–2020 normal ----
  const cells = geo.grid.filter((c) => c.weight > 0);
  const cellEntities = new Map<string, Entity>();
  for (const c of cells) {
    const e = viewer.entities.add({
      id: `cell:${c.id}`,
      show: false,
      rectangle: {
        coordinates: Rectangle.fromDegrees(
          c.lon - 0.3125 + 0.03,
          c.lat - 0.25 + 0.03,
          c.lon + 0.3125 - 0.03,
          c.lat + 0.25 - 0.03,
        ),
        height: 0,
        extrudedHeight: 1,
        material: MID,
        outline: true,
        outlineColor: Color.fromCssColorString('#f4f0e5').withAlpha(0.6),
      },
      position: Cartesian3.fromDegrees(c.lon, c.lat, 1),
      label: {
        text: '',
        font: '600 17px "Be Vietnam Pro", sans-serif',
        fillColor: Color.fromCssColorString('#0b160d'),
        showBackground: true,
        backgroundColor: Color.fromCssColorString('#f4f0e5').withAlpha(0.92),
        backgroundPadding: new Cartesian2(8, 5),
        verticalOrigin: VerticalOrigin.BOTTOM,
        pixelOffset: new Cartesian2(0, -6),
        disableDepthTestDistance: Number.POSITIVE_INFINITY,
        translucencyByDistance: new NearFarScalar(3e5, 1, 1.2e6, 0),
      },
    });
    cellEntities.set(c.id, e);
  }

  // ---- illustrative orbit rings and satellites ----
  const orbitEntities: Entity[] = [];
  let phase = 0;
  MISSIONS.forEach((m, k) => {
    const raan = 20 + k * 52;
    const pts = Array.from({ length: 181 }, (_, i) =>
      orbitPoint(m.altitudeKm, m.inclinationDeg, raan, (i / 180) * Math.PI * 2),
    );
    const color = Color.fromCssColorString(m.color);
    orbitEntities.push(
      viewer.entities.add({ show: false, polyline: { positions: pts, width: 1.4, material: color.withAlpha(0.55) } }),
    );
    orbitEntities.push(
      viewer.entities.add({
        show: false,
        position: new CallbackProperty(
          () => orbitPoint(m.altitudeKm, m.inclinationDeg, raan, phase * (7000 / (6371 + m.altitudeKm)) + k),
          false,
        ) as never,
        point: { pixelSize: 9, color, outlineColor: Color.BLACK, outlineWidth: 1.5 },
        label: {
          text: m.name,
          font: '600 17px "Be Vietnam Pro", sans-serif',
          fillColor: color,
          outlineColor: Color.BLACK,
          outlineWidth: 3,
          style: LabelStyle.FILL_AND_OUTLINE,
          pixelOffset: new Cartesian2(12, 0),
          horizontalOrigin: HorizontalOrigin.LEFT,
        },
      }),
    );
  });

  // ---- two flagship satellites, Viet Nam and NASA Terra, on drawn orbits that pass over Nghệ An ----
  let flagPhase = -0.55;
  const flagEntities: Entity[] = [];
  for (const f of FLAGSHIPS) {
    const frame = trackFrame(f.heading);
    const theta = () => flagPhase * (f.id === 'vn' ? 1 : 1.12) + f.offset;
    const near = () => Math.abs(wrap(theta())) < 0.2;
    const color = Color.fromCssColorString(f.color);
    flagEntities.push(
      viewer.entities.add({
        show: false,
        polyline: {
          positions: Array.from({ length: 241 }, (_, i) => trackPoint(frame, f.altKm, (i / 240) * Math.PI * 2)),
          width: 1.6,
          material: color.withAlpha(0.45),
        },
      }),
    );
    flagEntities.push(
      viewer.entities.add({
        show: false,
        position: new CallbackProperty(() => trackPoint(frame, f.altKm, theta()), false) as never,
        billboard: { image: satelliteImage(f.flag), width: 108, height: 65, verticalOrigin: VerticalOrigin.CENTER },
        label: {
          text: lang === 'vi' ? f.label.vi : f.label.en,
          font: '600 17px "Be Vietnam Pro", sans-serif',
          fillColor: color,
          outlineColor: Color.BLACK,
          outlineWidth: 3,
          style: LabelStyle.FILL_AND_OUTLINE,
          pixelOffset: new Cartesian2(0, 46),
          verticalOrigin: VerticalOrigin.TOP,
        },
      }),
    );
    // the scan beam: a cone from the satellite down to the ground, lit while the satellite is over the province
    flagEntities.push(
      viewer.entities.add({
        show: false,
        position: new CallbackProperty(() => trackPoint(frame, f.altKm / 2, theta()), false) as never,
        cylinder: {
          length: f.altKm * 1000,
          topRadius: 1500,
          bottomRadius: 85_000,
          material: new ColorMaterialProperty(color.withAlpha(0.2)),
          show: new CallbackProperty(near, false) as never,
        },
      }),
    );
  }

  let overlayLayer: ImageryLayer | null = null;
  let year = 2020;
  let selected = '';
  let raf = 0;
  let orbitsMoving = false;
  let flagsMoving = false;

  const requestRender = () => scene.requestRender();
  const paintCells = () => {
    for (const [id, e] of cellEntities) {
      const v = cellYear(id, year);
      const rect = e.rectangle;
      if (!rect) continue;
      const sel = id === selected;
      rect.extrudedHeight = (v ? Math.max(2000, v.rain * COLUMN_M_PER_MM) : 1500) as never;
      rect.material = (v ? anomalyColor(v.anomaly) : MID.withAlpha(0.4)) as never;
      rect.outlineColor = (
        sel ? Color.fromCssColorString('#e9bc57') : Color.fromCssColorString('#f4f0e5').withAlpha(0.6)
      ) as never;
      e.position = Cartesian3.fromDegrees(
        Number(id.split('_')[1]),
        Number(id.split('_')[0]),
        (v ? Math.max(2000, v.rain * COLUMN_M_PER_MM) : 1500) + 600,
      ) as never;
      if (e.label) e.label.text = (v ? `${Math.round(v.rain).toLocaleString(t.meta.locale)} mm` : '—') as never;
    }
    requestRender();
  };

  const tick = () => {
    if (orbitsMoving) phase += 0.0025;
    if (flagsMoving) flagPhase += 0.0018;
    scene.requestRender();
    raf = orbitsMoving || flagsMoving ? requestAnimationFrame(tick) : 0;
  };
  const restartTick = () => {
    cancelAnimationFrame(raf);
    raf = orbitsMoving || flagsMoving ? requestAnimationFrame(tick) : 0;
    requestRender();
  };

  const handler = new ScreenSpaceEventHandler(scene.canvas);
  handler.setInputAction((ev: { position: Cartesian2 }) => {
    const picked = scene.pick(ev.position) as { id?: Entity } | undefined;
    const id = picked?.id?.id;
    if (typeof id === 'string' && id.startsWith('cell:')) onPick(id.slice(5));
  }, ScreenSpaceEventType.LEFT_CLICK);

  return {
    goTo: (id, instant) => {
      const s = SCENES.find((x) => x.id === id) ?? SCENES[0];
      if (!s) return;
      const showCells = s.cells;
      for (const e of cellEntities.values()) e.show = showCells;
      for (const e of placeLabels) e.show = s.labels;
      const destination = Cartesian3.fromDegrees(s.camera.lon, s.camera.lat, s.camera.height);
      const orientation = {
        heading: CMath.toRadians(s.camera.heading),
        pitch: CMath.toRadians(s.camera.pitch),
        roll: 0,
      };
      viewer.camera.cancelFlight();
      if (instant) viewer.camera.setView({ destination, orientation });
      else viewer.camera.flyTo({ destination, orientation, duration: s.camera.duration, complete: requestRender });
      requestRender();
    },
    setYear: (y) => {
      year = y;
      paintCells();
    },
    setOverlay: (overlay, y, composite) => {
      if (overlayLayer) {
        viewer.imageryLayers.remove(overlayLayer, true);
        overlayLayer = null;
      }
      let provider: UrlTemplateImageryProvider | Promise<SingleTileImageryProvider> | null = null;
      if (overlay === 'ndvi-modis' && y >= 2001)
        provider = gibs('MODIS_Terra_L3_NDVI_16Day', 'GoogleMapsCompatible_Level9', 'png', `${y}-07-28`);
      if (overlay === 'imerg' && y >= 2001)
        provider = gibs('IMERG_Precipitation_Rate', 'GoogleMapsCompatible_Level6', 'png', `${y}-09-15`);
      if (overlay === 'smap' && y >= 2016)
        provider = gibs('SMAP_L4_Analyzed_Root_Zone_Soil_Moisture', 'GoogleMapsCompatible_Level6', 'png', `${y}-07-15`);
      if (overlay === 's2') {
        const c = VEG.composites.find((x) => x.id === composite) ?? VEG.composites[0];
        if (c) {
          const [w, so, e, n] = c.bounds;
          provider = SingleTileImageryProvider.fromUrl(c.png, {
            rectangle: Rectangle.fromDegrees(w, so, e, n),
            credit: 'Contains modified Copernicus Sentinel data 2020-2024',
          });
        }
      }
      if (!provider) {
        requestRender();
        return;
      }
      if (provider instanceof Promise) {
        provider
          .then((p) => {
            overlayLayer = viewer.imageryLayers.addImageryProvider(p);
            overlayLayer.alpha = 0.9;
            requestRender();
          })
          .catch(() => requestRender());
      } else {
        overlayLayer = viewer.imageryLayers.addImageryProvider(provider);
        overlayLayer.alpha = 0.75;
        requestRender();
      }
    },
    setSelected: (cell) => {
      selected = cell;
      paintCells();
    },
    setOrbits: (on, moving) => {
      for (const e of orbitEntities) e.show = on;
      orbitsMoving = on && moving;
      restartTick();
    },
    setFlagships: (on, moving) => {
      for (const e of flagEntities) e.show = on;
      flagsMoving = on && moving;
      restartTick();
    },
    stopFlight: () => viewer.camera.cancelFlight(),
    dispose: () => {
      cancelAnimationFrame(raf);
      handler.destroy();
      if (!viewer.isDestroyed()) viewer.destroy();
    },
  };
}

export const COMPOSITES = VEG.composites;
