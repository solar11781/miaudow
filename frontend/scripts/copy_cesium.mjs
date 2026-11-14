// Copies only the CesiumJS runtime files the Earth observatory uses (web workers, the star sky box, the Moon, the
// celestial-frame tables and the terrain-height index) next to the app, where CESIUM_BASE_URL points. The base map
// comes from NASA GIBS, so Cesium's bundled Natural Earth tiles, icons, widgets and 3D-model decoders are left out.
// Runs before `dev` and `build`; the copy is git-ignored.
import { cp, mkdir, readdir, rm } from 'node:fs/promises';
import path from 'node:path';

const SRC = path.resolve('node_modules', 'cesium', 'Build', 'Cesium');
const OUT = path.resolve('public', 'cesium');
const PARTS = [
  'Workers',
  'Assets/IAU2006_XYS',
  'Assets/Images',
  'Assets/Textures/SkyBox',
  'Assets/Textures/moonSmall.jpg',
  'Assets/approximateTerrainHeights.json',
];
// empty the folder rather than deleting it: a running dev server watches it, and Windows refuses to remove it
await mkdir(OUT, { recursive: true });
for (const entry of await readdir(OUT)) await rm(path.join(OUT, entry), { recursive: true, force: true });
for (const part of PARTS) {
  await mkdir(path.dirname(path.join(OUT, part)), { recursive: true });
  await cp(path.join(SRC, part), path.join(OUT, part), { recursive: true });
}
console.log('cesium runtime files copied to', OUT);
