// Builds the web image library: responsive AVIF + WebP files, a tiny blurred placeholder,
// the dominant colour and the size of every real photo and every concept illustration.
//
// Run from web/:  node pipeline/build_media.mjs
//
// Inputs
//   ../assets/photos/originals/*          real photographs (licence data in ../assets/photos/PHOTO_MANIFEST.json)
//   ../assets/concept-graded/*.webp       AI-generated concept illustrations (described in ART below)
// Outputs
//   public/media/photo/<slug>-<w>.{avif,webp}
//   public/media/art/<slug>-<w>.{avif,webp}
//   src/data/generated/media.json         web-facing manifest (paths relative, no leading slash, for Vite base './')
//
// Real photos get one mild, uniform colour grade (GRADE below). Its exact wording is also stored in
// PHOTO_MANIFEST.json "modification", which matters for CC BY-SA photos: the graded files are derivatives.
// Illustrations are only resized and re-encoded.
import { existsSync } from 'node:fs';
import { mkdir, readdir, readFile, rm, stat, writeFile } from 'node:fs/promises';
import path from 'node:path';
import sharp from 'sharp';

const ROOT = path.resolve('..');
const PHOTO_SRC = path.join(ROOT, 'assets', 'photos', 'originals');
const PHOTO_MANIFEST = path.join(ROOT, 'assets', 'photos', 'PHOTO_MANIFEST.json');
const ART_SRC = path.join(ROOT, 'assets', 'concept-graded');
const OUT = path.resolve('public', 'media');
const JSON_OUT = path.resolve('src', 'data', 'generated', 'media.json');

const WIDTHS = [640, 1280, 1920];
const AVIF = { quality: 55, effort: 4 };
const WEBP = { quality: 78, effort: 5 };

// "Lam Giang golden": +3 % saturation, red x1.02, blue x0.97. Kept deliberately small so photos stay natural.
// This exact operation is recorded in each PHOTO_MANIFEST.json "modification" field; change both together.
const grade = (img) => img.modulate({ saturation: 1.03 }).linear([1.02, 1, 0.97], [0, 0, 0]);

// Where each photo is meant to go in the interface. Anything not listed is a card.
const PHOTO_USE = {
  'do-luong-nam-son-road-rice': 'hero',
  'nam-dan-ql46-rice-plain': 'hero',
  'lam-river-vinh-ben-thuy': 'section',
  'con-cuong-lam-river-chau-khe': 'section',
  'con-cuong-chau-khe-rice-field': 'section',
  'con-cuong-mon-son-road-rice': 'section',
  'con-cuong-binh-chuan-water-wheels': 'section',
};

const ART_CAPTION_PREFIX = {
  vi: 'Tranh minh họa, không phải ảnh chụp Nghệ An.',
  en: 'Illustration, not a photograph of Nghệ An.',
};
const ART_GEOGRAPHY = {
  vi: 'Không phải địa điểm thật; tranh do máy tạo, không gắn với Nghệ An',
  en: 'Not a real place; machine-generated picture, not located in Nghệ An',
};

// The 16 concept illustrations, described from what is actually visible (see assets/ART_REVIEW.md).
const ART = {
  a1_horizon_golden: {
    slug: 'a1-horizon', use: 'section', focal: { x: 30, y: 45 },
    alt: { vi: 'Tranh: ruộng lúa chín vàng lúc mặt trời lặn, một con mương nhỏ uốn quanh bờ ruộng, đồi núi mờ phía xa', en: 'Illustration: ripe golden rice field at sunset, a small ditch curving along the bund, hazy hills behind' },
    caption: { vi: 'Ruộng lúa chín và mương nước lúc hoàng hôn.', en: 'Ripe rice and an irrigation ditch at sunset.' },
  },
  a2_fields_golden: {
    slug: 'a2-fields', use: 'avoid', focal: { x: 50, y: 50 },
    alt: { vi: 'Tranh: nhìn từ trên cao xuống các thửa ruộng xanh, vàng và ruộng ngập nước, một con kênh chạy chéo', en: 'Illustration: aerial view of green, golden and flooded rice plots with a canal running diagonally' },
    caption: { vi: 'Các thửa ruộng nhìn từ trên cao.', en: 'Rice plots seen from above.' },
  },
  a3_rice_golden: {
    slug: 'a3-rice', use: 'card', focal: { x: 30, y: 45 },
    alt: { vi: 'Tranh: cận cảnh bông lúa chín đọng sương, phía sau là dòng sông và đồi trong sương sớm', en: 'Illustration: close-up of ripe rice panicles with dew, a river and hills in morning mist behind' },
    caption: { vi: 'Bông lúa chín trong sương sớm.', en: 'Ripe rice panicles in morning mist.' },
  },
  a4_river_golden: {
    slug: 'a4-river', use: 'section', focal: { x: 55, y: 55 },
    alt: { vi: 'Tranh: dòng sông rộng chảy giữa bãi cỏ và hàng cây, núi xa trong sương, mặt trời mọc', en: 'Illustration: a wide river between grassy banks and trees, distant mountains in mist, sunrise' },
    caption: { vi: 'Dòng sông và đồng bãi lúc bình minh.', en: 'A river and its floodplain at sunrise.' },
  },
  b1_horizon_golden: {
    slug: 'b1-horizon', use: 'section', focal: { x: 45, y: 60 },
    alt: { vi: 'Tranh: cánh đồng lúa xanh vàng, con đường đất và mương nước song song, mặt trời lặn sau đồi', en: 'Illustration: green-gold rice field, a dirt track beside a water ditch, sun setting behind hills' },
    caption: { vi: 'Đường đất ven mương giữa đồng lúa.', en: 'A dirt track beside a ditch through rice fields.' },
  },
  b2_fields_golden: {
    slug: 'b2-fields', use: 'avoid', focal: { x: 50, y: 50 },
    alt: { vi: 'Tranh: nhìn từ trên cao xuống ruộng lúa xanh và vàng, một con kênh có hàng cây chạy dọc', en: 'Illustration: aerial view of green and golden rice plots with a tree-lined canal' },
    caption: { vi: 'Ruộng lúa và kênh nước nhìn từ trên cao.', en: 'Rice plots and a canal seen from above.' },
  },
  b3_rice_golden: {
    slug: 'b3-rice', use: 'card', focal: { x: 45, y: 45 },
    alt: { vi: 'Tranh: cận cảnh bông lúa chín vàng, cánh đồng và đồi mờ phía sau', en: 'Illustration: close-up of ripe golden rice panicles, field and hazy hill behind' },
    caption: { vi: 'Bông lúa chín trên đồng.', en: 'Ripe rice panicles in the field.' },
  },
  b4_river_golden: {
    slug: 'b4-river', use: 'section', focal: { x: 60, y: 55 },
    alt: { vi: 'Tranh: dòng sông phẳng lặng phản chiếu hàng cây, đồng lúa và núi trong sương sớm', en: 'Illustration: calm river reflecting trees, rice fields and mountains in morning mist' },
    caption: { vi: 'Sông và đồng lúa trong sương sớm.', en: 'River and rice fields in morning mist.' },
  },
  c1_horizon_golden: {
    slug: 'c1-horizon', use: 'section', focal: { x: 55, y: 60 },
    alt: { vi: 'Tranh: cánh đồng lúa chín rộng, con mương nhỏ bên trái, trời hoàng hôn nhiều mây', en: 'Illustration: wide ripe rice field, a small ditch on the left, cloudy sunset sky' },
    caption: { vi: 'Đồng lúa chín và mương nước lúc chiều tối.', en: 'Ripe rice and a ditch in the evening.' },
  },
  c2_fields_golden: {
    slug: 'c2-fields', use: 'section', focal: { x: 55, y: 50 },
    alt: { vi: 'Tranh: nhìn từ trên cao xuống các thửa ruộng xanh vàng, con kênh nhỏ uốn lượn, hàng cây ven bờ', en: 'Illustration: aerial view of green and golden rice plots, a small winding canal, trees on the banks' },
    caption: { vi: 'Kênh nước nhỏ chảy giữa các thửa ruộng.', en: 'A small canal winding between rice plots.' },
  },
  c3_rice_golden: {
    slug: 'c3-rice', use: 'card', focal: { x: 40, y: 45 },
    alt: { vi: 'Tranh: cận cảnh bông lúa chín, nắng sớm chiếu từ phía sau, cánh đồng mờ sương', en: 'Illustration: close-up of ripe rice panicles backlit by early sun, misty field behind' },
    caption: { vi: 'Bông lúa chín trong nắng sớm.', en: 'Ripe rice panicles in early sunlight.' },
  },
  c4_river_golden: {
    slug: 'c4-river', use: 'section', focal: { x: 45, y: 45 },
    alt: { vi: 'Tranh: mặt sông phủ sương, bãi bồi có cây lớn, đồi núi xanh phía sau', en: 'Illustration: misty river surface, a riverbank with large trees, green hills behind' },
    caption: { vi: 'Bãi sông trong sương sớm.', en: 'A riverbank in morning mist.' },
  },
  d1_horizon_golden: {
    slug: 'd1-horizon', use: 'hero', focal: { x: 50, y: 60 },
    alt: { vi: 'Tranh: cánh đồng lúa chín trải rộng, con mương uốn cong ở giữa, mặt trời lặn sau dãy đồi', en: 'Illustration: wide ripe rice field, a curving ditch in the middle, sun setting behind a ridge' },
    caption: { vi: 'Đồng lúa chín và mương nước lúc hoàng hôn.', en: 'Ripe rice fields and a ditch at sunset.' },
  },
  d2_fields_golden: {
    slug: 'd2-fields', use: 'card', focal: { x: 55, y: 45 },
    alt: { vi: 'Tranh: nhìn từ trên cao xuống ruộng lúa xanh vàng, con mương uốn lượn, ao nhỏ và hàng dừa', en: 'Illustration: aerial view of green and golden rice plots, a winding ditch, a small pond and palm trees' },
    caption: { vi: 'Mương nước và ao nhỏ giữa đồng lúa.', en: 'A ditch and a small pond among rice plots.' },
  },
  d3_rice_golden: {
    slug: 'd3-rice', use: 'card', focal: { x: 40, y: 45 },
    alt: { vi: 'Tranh: cận cảnh chùm bông lúa chín trĩu hạt, đồng lúa và hàng cây trong sương', en: 'Illustration: close-up of heavy ripe rice panicles, field and trees in mist behind' },
    caption: { vi: 'Bông lúa chín trĩu hạt.', en: 'Heavy ripe rice panicles.' },
  },
  d4_river_golden: {
    slug: 'd4-river', use: 'section', focal: { x: 50, y: 60 },
    alt: { vi: 'Tranh: dòng sông rộng lúc bình minh, bờ có cây và bãi cỏ, núi thấp trong sương', en: 'Illustration: wide river at sunrise, banks with trees and grass, low mountains in mist' },
    caption: { vi: 'Sông rộng lúc bình minh.', en: 'A wide river at sunrise.' },
  },
};

const hex = ({ r, g, b }) => `#${[r, g, b].map((v) => v.toString(16).padStart(2, '0')).join('')}`;

async function orientedSize(file) {
  const m = await sharp(file).metadata();
  const swap = (m.orientation ?? 1) >= 5;
  return swap ? { width: m.height, height: m.width } : { width: m.width, height: m.height };
}

function widthsFor(width) {
  const list = WIDTHS.filter((w) => w < width);
  if (width <= WIDTHS.at(-1)) list.push(width); // largest file = original width, never upscaled
  else list.push(WIDTHS.at(-1));
  return [...new Set(list)].sort((a, b) => a - b);
}

async function render(file, kind, slug, isPhoto) {
  const dir = path.join(OUT, kind);
  const { width, height } = await orientedSize(file);
  const base = () => {
    const img = sharp(file).rotate();
    return isPhoto ? grade(img) : img;
  };
  const sources = [];
  for (const w of widthsFor(width)) {
    const name = `${slug}-${w}`;
    await base().resize({ width: w }).avif(AVIF).toFile(path.join(dir, `${name}.avif`));
    await base().resize({ width: w }).webp(WEBP).toFile(path.join(dir, `${name}.webp`));
    sources.push({ w, avif: `media/${kind}/${name}.avif`, webp: `media/${kind}/${name}.webp` });
  }
  const lqip = await base().resize({ width: 24 }).blur(1.2).webp({ quality: 40 }).toBuffer();
  const { dominant } = await base().resize({ width: 256 }).toBuffer().then((b) => sharp(b).stats());
  return {
    width,
    height,
    sources,
    placeholder: `data:image/webp;base64,${lqip.toString('base64')}`,
    dominant: hex(dominant),
  };
}

async function dirBytes(dir) {
  let total = 0;
  for (const f of await readdir(dir)) total += (await stat(path.join(dir, f))).size;
  return total;
}

for (const kind of ['photo', 'art']) {
  await rm(path.join(OUT, kind), { recursive: true, force: true });
  await mkdir(path.join(OUT, kind), { recursive: true });
}

const media = {};

// Real photographs
const manifest = JSON.parse(await readFile(PHOTO_MANIFEST, 'utf8'));
const listed = new Set(manifest.photos.map((p) => p.filename));
for (const f of await readdir(PHOTO_SRC)) {
  if (!listed.has(f)) console.warn(`skip ${f}: not in PHOTO_MANIFEST.json`);
}
for (const p of manifest.photos) {
  const file = path.join(PHOTO_SRC, p.filename);
  if (!existsSync(file)) throw new Error(`missing original ${file}`);
  const r = await render(file, 'photo', p.asset_id, true);
  const shortLicense = p.license;
  media[p.asset_id] = {
    kind: 'photo',
    ...r,
    focal: p.focal_point,
    alt: p.alt,
    caption: p.caption,
    credit: {
      vi: p.attribution,
      en: p.attribution.replace(/^Ảnh:/, 'Photo:').replace('(đã chỉnh màu nhẹ)', '(colour lightly adjusted)'),
    },
    license: shortLicense,
    license_url: p.license_url,
    source_url: p.source_url,
    geography: p.geography,
    is_study_area: p.is_study_area,
    use: PHOTO_USE[p.asset_id] ?? 'card',
  };
  console.log('photo', p.asset_id, `${r.width}x${r.height}`, r.sources.map((s) => s.w).join(','));
}

// Concept illustrations
for (const f of (await readdir(ART_SRC)).filter((n) => /\.(webp|png|jpe?g)$/i.test(n)).sort()) {
  const key = path.parse(f).name;
  const meta = ART[key];
  if (!meta) {
    console.warn(`skip ${f}: no description in ART`);
    continue;
  }
  const r = await render(path.join(ART_SRC, f), 'art', meta.slug, false);
  media[meta.slug] = {
    kind: 'illustration',
    ...r,
    focal: meta.focal,
    alt: meta.alt,
    caption: {
      vi: `${ART_CAPTION_PREFIX.vi} ${meta.caption.vi}`,
      en: `${ART_CAPTION_PREFIX.en} ${meta.caption.en}`,
    },
    credit: null,
    license: null,
    license_url: null,
    source_url: null,
    geography: ART_GEOGRAPHY,
    is_study_area: false,
    use: meta.use,
  };
  console.log('art', meta.slug, `${r.width}x${r.height}`, r.sources.map((s) => s.w).join(','), meta.use);
}

await mkdir(path.dirname(JSON_OUT), { recursive: true });
await writeFile(JSON_OUT, `${JSON.stringify(media, null, 1)}\n`);
const photoBytes = await dirBytes(path.join(OUT, 'photo'));
const artBytes = await dirBytes(path.join(OUT, 'art'));
console.log(`media.json: ${Object.keys(media).length} entries -> ${JSON_OUT}`);
console.log(`bytes: photo ${photoBytes}, art ${artBytes}, total ${photoBytes + artBytes}`);
