// Two flagship satellites for the observatory: one flies the flag of Viet Nam, one is NASA's Terra (MODIS, the source
// of the app's farmland weights) with the flag of the United States. Both are illustrations: their orbits are drawn to
// pass over Nghệ An, not computed from real ephemerides, and the page says so. No agency insignia is drawn (NASA's
// insignia may not be used on non-NASA products).
import { Cartesian3, Math as CMath } from 'cesium';

export type Flag = 'vn' | 'us';

export interface Flagship {
  id: string;
  flag: Flag;
  /** Direction of travel over Nghệ An, degrees clockwise from north. */
  heading: number;
  altKm: number;
  /** Phase offset along the orbit, radians. */
  offset: number;
  label: { vi: string; en: string };
  color: string;
}

export const FLAGSHIPS: Flagship[] = [
  { id: 'vn', flag: 'vn', heading: -14, altKm: 680, offset: 0, label: { vi: 'Việt Nam · vệ tinh minh họa', en: 'Viet Nam · illustrative satellite' }, color: '#f1d38c' },
  { id: 'terra', flag: 'us', heading: 196, altKm: 705, offset: 0.9, label: { vi: 'NASA Terra · MODIS', en: 'NASA Terra · MODIS' }, color: '#85c0e6' },
];

/** The point over which both orbits pass: Nghệ An, between Đô Lương and Vinh. */
const TARGET = { lat: 19.0, lon: 105.2 };

/** Orbit frame through the target: t points at the target, u along the direction of travel. */
export function trackFrame(headingDeg: number) {
  const phi = CMath.toRadians(TARGET.lat), lam = CMath.toRadians(TARGET.lon), h = CMath.toRadians(headingDeg);
  const t = new Cartesian3(Math.cos(phi) * Math.cos(lam), Math.cos(phi) * Math.sin(lam), Math.sin(phi));
  const n = new Cartesian3(-Math.sin(phi) * Math.cos(lam), -Math.sin(phi) * Math.sin(lam), Math.cos(phi));
  const e = new Cartesian3(-Math.sin(lam), Math.cos(lam), 0);
  const u = new Cartesian3(n.x * Math.cos(h) + e.x * Math.sin(h), n.y * Math.cos(h) + e.y * Math.sin(h), n.z * Math.cos(h) + e.z * Math.sin(h));
  return { t, u };
}

/** A point of the great-circle orbit `theta` radians past the target, at `altKm` above a spherical Earth. */
export function trackPoint(f: { t: Cartesian3; u: Cartesian3 }, altKm: number, theta: number): Cartesian3 {
  const r = 6_371_000 + altKm * 1000;
  const c = Math.cos(theta), s = Math.sin(theta);
  return new Cartesian3(r * (c * f.t.x + s * f.u.x), r * (c * f.t.y + s * f.u.y), r * (c * f.t.z + s * f.u.z));
}

/** theta folded into (-π, π]: 0 is right over Nghệ An. */
export const wrap = (theta: number) => Math.atan2(Math.sin(theta), Math.cos(theta));

const FLAGS: Record<Flag, string> = {
  vn: '<rect x="49" y="29" width="22" height="15" fill="#DA251D"/><polygon points="60,31.2 61.6,35.6 66.2,35.7 62.5,38.5 63.9,43 60,40.3 56.1,43 57.5,38.5 53.8,35.7 58.4,35.6" fill="#FFFF00"/>',
  us: '<rect x="49" y="29" width="22" height="15" fill="#B22234"/>'
    + [1, 3, 5, 7, 9, 11, 13].map((i) => `<rect x="49" y="${29 + i * (15 / 15)}" width="22" height="1.1" fill="#FFFFFF"/>`).join('')
    + '<rect x="49" y="29" width="9.5" height="8" fill="#3C3B6E"/>',
};

const panel = (x: number) => {
  const cells = Array.from({ length: 5 }, (_, i) => `<line x1="${x + 7.6 * (i + 1)}" y1="26" x2="${x + 7.6 * (i + 1)}" y2="46" stroke="#7fb0de" stroke-width=".7"/>`).join('');
  return `<rect x="${x}" y="26" width="38" height="20" rx="1.5" fill="#173a6b" stroke="#9cc3e6" stroke-width=".8"/>${cells}<line x1="${x}" y1="36" x2="${x + 38}" y2="36" stroke="#7fb0de" stroke-width=".7"/>`;
};

/** A satellite drawn as an image for a Cesium billboard: gold-foil body with the flag, two solar wings, a dish. */
export function satelliteImage(flag: Flag): string {
  const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="120" height="72" viewBox="0 0 120 72">`
    + panel(2) + panel(80)
    + '<rect x="40" y="34.5" width="6" height="3" fill="#c9ccd1"/><rect x="74" y="34.5" width="6" height="3" fill="#c9ccd1"/>'
    + '<rect x="46" y="22" width="28" height="28" rx="3" fill="#c8932f" stroke="#f1d38c" stroke-width="1.2"/>'
    + '<path d="M46 30h28M46 42h28" stroke="#a87a22" stroke-width=".8"/>'
    + FLAGS[flag]
    + '<line x1="60" y1="50" x2="60" y2="57" stroke="#e6e8ea" stroke-width="1.6"/><ellipse cx="60" cy="59" rx="9" ry="3.4" fill="#e6e8ea" stroke="#9aa3ab" stroke-width=".6"/>'
    + '<circle cx="60" cy="15" r="4" fill="#0b1a12" stroke="#f1d38c" stroke-width="1.2"/><line x1="60" y1="19" x2="60" y2="22" stroke="#f1d38c" stroke-width="1.2"/>'
    + '</svg>';
  return `data:image/svg+xml;charset=utf-8,${encodeURIComponent(svg)}`;
}
