// H15: the satellite labels come from the vi and en text files.
import { describe, expect, it } from 'vitest';
import { en } from '../../i18n/en';
import { vi } from '../../i18n/vi';
import { FLAGSHIPS, satelliteImage } from './flagships';

describe('flagship satellites', () => {
  it('take their labels from the text files', () => {
    expect(FLAGSHIPS.map((f) => f.label)).toEqual([
      { vi: vi.earth.flagships.vn, en: en.earth.flagships.vn },
      { vi: vi.earth.flagships.terra, en: en.earth.flagships.terra },
    ]);
  });
});

// Vietnam's flag (Constitution art. 13; the drawing rule this repo uses in cinema/parts.tsx): 3:2, red field, a yellow
// five-pointed star centred, its points on a circle of radius 0.3 x the flag height
describe('the flag on the globe satellite', () => {
  it('draws the Vietnamese star centred with points on a circle of 0.3 x the height', () => {
    const svg = satelliteImage('vn');
    const decoded = decodeURIComponent(svg.slice(svg.indexOf(',') + 1));
    const rect = /<rect x="([\d.]+)" y="([\d.]+)" width="([\d.]+)" height="([\d.]+)" fill="#DA251D"/.exec(decoded);
    const star = /<polygon points="([^"]+)" fill="#FFFF00"/.exec(decoded);
    expect(rect).not.toBeNull();
    expect(star).not.toBeNull();
    const [x = 0, y = 0, w = 0, h = 1] = (rect?.slice(1) ?? []).map(Number);
    expect(w / h).toBeCloseTo(1.5, 2);
    const pts = (star?.[1] ?? '').split(' ').map((p) => p.split(',').map(Number));
    const cx = x + w / 2;
    const cy = y + h / 2;
    const outer = pts.filter((_, i) => i % 2 === 0).map(([px = 0, py = 0]) => Math.hypot(px - cx, py - cy));
    for (const d of outer) expect(d).toBeCloseTo(0.3 * h, 1);
  });
});
