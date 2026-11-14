// The observatory as a state machine: each scene has a camera, the layers it shows and what the side panel holds.
// Camera flights are user-started and can be interrupted at any time; under reduced motion the camera jumps.

export type SceneId = 'cosmos' | 'earth' | 'satellites' | 'vietnam' | 'nghe-an' | 'do-luong' | 'analysis' | 'insight';
export type Panel = 'story' | 'missions' | 'layers' | 'metric' | 'insight';

export interface Scene {
  id: SceneId;
  camera: { lon: number; lat: number; height: number; heading: number; pitch: number; duration: number };
  /** Farmland cells as data columns. */
  cells: boolean;
  /** Illustrative orbit rings. */
  orbits: boolean;
  /** Place names (drawn by the app). */
  labels: boolean;
  panel: Panel;
}

export const SCENES: Scene[] = [
  {
    id: 'cosmos',
    camera: { lon: 112, lat: 8, height: 62_000_000, heading: 0, pitch: -90, duration: 2.5 },
    cells: false,
    orbits: false,
    labels: false,
    panel: 'story',
  },
  {
    id: 'earth',
    camera: { lon: 106, lat: 14, height: 17_000_000, heading: 0, pitch: -90, duration: 3 },
    cells: false,
    orbits: false,
    labels: false,
    panel: 'story',
  },
  {
    id: 'satellites',
    camera: { lon: 96, lat: 4, height: 24_000_000, heading: 0, pitch: -90, duration: 3 },
    cells: false,
    orbits: true,
    labels: false,
    panel: 'missions',
  },
  {
    id: 'vietnam',
    camera: { lon: 106.4, lat: 16.0, height: 2_900_000, heading: 0, pitch: -88, duration: 3.5 },
    cells: false,
    orbits: false,
    labels: true,
    panel: 'story',
  },
  {
    id: 'nghe-an',
    camera: { lon: 104.95, lat: 17.55, height: 230_000, heading: 4, pitch: -52, duration: 3.5 },
    cells: false,
    orbits: false,
    labels: true,
    panel: 'layers',
  },
  {
    id: 'do-luong',
    camera: { lon: 105.33, lat: 18.62, height: 34_000, heading: 2, pitch: -48, duration: 3 },
    cells: false,
    orbits: false,
    labels: true,
    panel: 'layers',
  },
  {
    id: 'analysis',
    camera: { lon: 105.3, lat: 17.05, height: 200_000, heading: 0, pitch: -40, duration: 3 },
    cells: true,
    orbits: false,
    labels: false,
    panel: 'metric',
  },
  {
    id: 'insight',
    camera: { lon: 105.3, lat: 17.05, height: 200_000, heading: 0, pitch: -40, duration: 1.5 },
    cells: true,
    orbits: false,
    labels: false,
    panel: 'insight',
  },
];

export const SCENE_IDS = SCENES.map((s) => s.id);
export const isScene = (v: string | null): v is SceneId => !!v && (SCENE_IDS as string[]).includes(v);
