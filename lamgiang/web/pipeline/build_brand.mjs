// Builds the Miaudow brand files from the team's logo sheet (assets/brand/miaudow-logo-sheet.png, designed by member B):
// the rounded app icon, the emblem on a transparent background and a light wordmark for dark surfaces.
//
// Run from web/:  node pipeline/build_brand.mjs
// Outputs public/brand/: icon-{32,48,96,180,512}.png, emblem-{360,720}.webp, wordmark-light-{360,720}.webp
import { mkdir } from 'node:fs/promises';
import path from 'node:path';
import sharp from 'sharp';

const SRC = path.resolve('..', 'assets', 'brand', 'miaudow-logo-sheet.png');
const OUT = path.resolve('public', 'brand');
const PAPER = [249, 231, 203]; // the sheet's paper colour, keyed out

/** The dark-green app icon square: found by its colour in the lower right of the sheet. */
async function iconBox(W, H, data, c) {
  let x0 = W, y0 = H, x1 = 0, y1 = 0;
  for (let y = Math.floor(H * 0.5); y < Math.floor(H * 0.88); y++) {
    for (let x = Math.floor(W * 0.6); x < W; x++) {
      const i = (y * W + x) * c;
      const [r, g, b] = [data[i], data[i + 1], data[i + 2]];
      if (g > 50 && g < 110 && r < 60 && b < 60) { x0 = Math.min(x0, x); x1 = Math.max(x1, x); y0 = Math.min(y0, y); y1 = Math.max(y1, y); }
    }
  }
  return { left: x0 + 2, top: y0 + 2, width: x1 - x0 - 3, height: y1 - y0 - 3 };
}

/** Removes the paper; with `light`, every non-orange pixel becomes ivory so the wordmark reads on dark green. */
async function cutOut(region, light) {
  const { data, info } = await sharp(SRC).extract(region).removeAlpha().raw().toBuffer({ resolveWithObject: true });
  const { width: W, height: H, channels: c } = info;
  const alpha = Buffer.alloc(W * H);
  const rgb = Buffer.alloc(W * H * 3);
  for (let p = 0; p < W * H; p++) {
    let [r, g, b] = [data[p * c], data[p * c + 1], data[p * c + 2]];
    const dist = Math.hypot(r - PAPER[0], g - PAPER[1], b - PAPER[2]);
    alpha[p] = Math.round(255 * Math.max(0, Math.min(1, (dist - 26) / 30)));
    if (light && !(r > 150 && r > g + 40 && g > b)) [r, g, b] = [243, 239, 226];
    rgb.set([r, g, b], p * 3);
  }
  const smooth = await sharp(alpha, { raw: { width: W, height: H, channels: 1 } }).median(3).extractChannel(0).raw().toBuffer({ resolveWithObject: true });
  const rgba = Buffer.alloc(W * H * 4);
  for (let p = 0; p < W * H; p++) {
    rgba.set([rgb[p * 3], rgb[p * 3 + 1], rgb[p * 3 + 2], smooth.data[p * smooth.info.channels]], p * 4);
  }
  return sharp(rgba, { raw: { width: W, height: H, channels: 4 } }).trim({ threshold: 1 }).png().toBuffer();
}

await mkdir(OUT, { recursive: true });
const { data, info } = await sharp(SRC).removeAlpha().raw().toBuffer({ resolveWithObject: true });
const W = info.width, H = info.height;

const box = await iconBox(W, H, data, info.channels);
const radius = Math.round(box.width * 0.22);
const mask = Buffer.from(`<svg width="${box.width}" height="${box.height}"><rect width="${box.width}" height="${box.height}" rx="${radius}" fill="#fff"/></svg>`);
const icon = await sharp(SRC).extract(box).composite([{ input: mask, blend: 'dest-in' }]).png().toBuffer();
for (const s of [32, 48, 96, 180, 512]) await sharp(icon).resize(s, s).png({ palette: true, quality: 92, compressionLevel: 9 }).toFile(path.join(OUT, `icon-${s}.png`));

const emblem = await cutOut({ left: 20, top: 20, width: Math.round(W * 0.355), height: Math.round(H * 0.41) }, false);
const word = await cutOut({ left: Math.round(W * 0.375), top: Math.round(H * 0.19), width: Math.round(W * 0.58), height: Math.round(H * 0.13) }, true);
for (const [name, img] of [['emblem', emblem], ['wordmark-light', word]]) {
  for (const w of [360, 720]) {
    await sharp(img).resize({ width: w }).webp({ quality: 88 }).toFile(path.join(OUT, `${name}-${w}.webp`));
  }
}
console.log('brand files in', OUT);
