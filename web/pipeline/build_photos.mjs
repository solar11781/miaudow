// Turns the team's source photos into responsive WebP files plus a tiny blurred placeholder for each.
// Usage: npm run photos -- <folder with the team photos>
// Only photos without a visible third-party watermark and without children are listed here (see src/data/photos.ts).
// The source photos are not committed; only the generated WebP files are.
import { mkdir, writeFile } from 'node:fs/promises';
import path from 'node:path';
import sharp from 'sharp';

if (!process.argv[2]) {
  console.error('usage: npm run photos -- <folder with the team photos>');
  process.exit(1);
}
const SRC = path.resolve(process.argv[2]);
const OUT = path.resolve('public', 'photos');
const MANIFEST = path.resolve('src', 'data', 'generated', 'photos.json');
const WIDTHS = [480, 960, 1440];

const PHOTOS = {
  'ganh-ma': 'image15.png',
  'dap-lua': 'image3.png',
  'canh-dong-tren-cao': 'image7.png',
  'dam-sen': 'image.png',
  'la-sen-non-la': 'image14.png',
  'phoi-tuong': 'image21.png',
  'doi-che': 'image16.png',
  'bac-thang-song': 'image5.png',
  'bac-thang-duong': 'image9.png',
  'bac-thang-nang': 'image10.png',
  'bac-thang-gat': 'image18.png',
};

await mkdir(OUT, { recursive: true });
const manifest = {};
for (const [slug, file] of Object.entries(PHOTOS)) {
  const input = sharp(path.join(SRC, file)).rotate();
  const { width, height } = await input.metadata();
  const widths = [...new Set(WIDTHS.filter((w) => w < width).concat(Math.min(width, 1440)))].sort((a, b) => a - b);
  const sources = [];
  for (const w of widths) {
    const name = `${slug}-${w}.webp`;
    await input.clone().resize({ width: w }).webp({ quality: 80, effort: 5 }).toFile(path.join(OUT, name));
    sources.push({ w, src: `photos/${name}` });
  }
  const lqip = await input.clone().resize({ width: 24 }).blur(1.2).webp({ quality: 40 }).toBuffer();
  const { dominant } = await input.clone().stats();
  manifest[slug] = {
    width,
    height,
    sources,
    placeholder: `data:image/webp;base64,${lqip.toString('base64')}`,
    dominant: `rgb(${dominant.r},${dominant.g},${dominant.b})`,
  };
  console.log(slug, `${width}x${height}`, widths.join(','));
}
await writeFile(MANIFEST, `${JSON.stringify(manifest, null, 1)}\n`);
console.log('manifest', MANIFEST);
