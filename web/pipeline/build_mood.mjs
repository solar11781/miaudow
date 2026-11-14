// Builds the mood photographs the team supplied (folder photoS_aesthetics_vietfarm next to this repository) into the
// same responsive AVIF + WebP form as build_media.mjs. Their authors and licences are not recorded and several carry
// a photographer's signature, so the outputs stay on this machine: public/media/mood/ and
// src/data/generated/media.mood.json are git-ignored, and the app falls back to the licensed photos without them.
//
// Run from web/:  node pipeline/build_mood.mjs [sourceDir]
import { existsSync } from 'node:fs';
import { mkdir, rm, writeFile } from 'node:fs/promises';
import path from 'node:path';
import sharp from 'sharp';

const SRC = path.resolve(process.argv[2] ?? path.join('..', '..', 'photoS_aesthetics_vietfarm'));
const OUT = path.resolve('public', 'media', 'mood');
const JSON_OUT = path.resolve('src', 'data', 'generated', 'media.mood.json');
const WIDTHS = [640, 1280, 1920];

// Described from what is visible; no place is claimed, because the source folder names none.
// `mark` records a visible signature or logo; it is never cropped or covered.
const MOOD = [
  { file: 'image.png', slug: 'lotus-boat', focal: [50, 45], mark: null,
    alt: ['Nhìn từ trên cao: chiếc thuyền nhỏ giữa đầm sen nở hoa', 'Seen from above: a small boat among flowering lotus'] },
  { file: 'image3.png', slug: 'winnowing', focal: [45, 35], mark: null,
    alt: ['Người nông dân đội nón tung lúa trong nắng ngược, hạt thóc bay', 'A farmer in a conical hat tossing rice stalks in backlight, grains flying'] },
  { file: 'image4.png', slug: 'buffalo-child', focal: [45, 40], mark: null,
    alt: ['Em nhỏ áo đỏ cưỡi trâu giữa cánh đồng xanh', 'A child in red riding a water buffalo across green fields'] },
  { file: 'image5.png', slug: 'river-terraces', focal: [55, 50], mark: null,
    alt: ['Nhìn từ trên cao: dòng sông xanh uốn quanh ruộng bậc thang, một chiếc thuyền', 'Seen from above: a green river curving past terraced fields, one boat'] },
  { file: 'image6.png', slug: 'boat-produce', focal: [50, 45], mark: 'logo "GA", bottom right',
    alt: ['Thuyền chở rau quả trên mặt nước có lá súng', 'A boat loaded with produce on water with lily pads'] },
  { file: 'image7.png', slug: 'field-ditch-workers', focal: [45, 50], mark: null,
    alt: ['Nhìn từ trên cao: người làm đồng đội nón đi dọc con mương giữa ruộng xanh', 'Seen from above: farm workers in conical hats walking along a ditch through green fields'] },
  { file: 'image8.png', slug: 'valley-village', focal: [50, 60], mark: '"© by Le Khanh", bottom right',
    alt: ['Thung lũng có ruộng lúa, nhà và con suối dưới núi', 'A valley with rice fields, houses and a stream below the hills'] },
  { file: 'image9.png', slug: 'terraces-road', focal: [50, 50], mark: null,
    alt: ['Ruộng bậc thang và con đường đất uốn qua sườn núi', 'Rice terraces and a dirt road winding over a hillside'] },
  { file: 'image10.png', slug: 'terraces-sunbeams', focal: [50, 55], mark: null,
    alt: ['Nắng xuyên sương xuống ruộng bậc thang và dòng suối', 'Sunbeams through mist over terraced fields and a stream'] },
  { file: 'image11.png', slug: 'karst-valley', focal: [50, 60], mark: '"Le Hong Ha" signature, top',
    alt: ['Thung lũng lúa chín vàng giữa núi đá vôi, nắng chiếu qua mây', 'A valley of ripe rice between limestone peaks, light through clouds'] },
  { file: 'image12.png', slug: 'karst-river-sunset', focal: [60, 55], mark: 'signature, bottom left',
    alt: ['Dòng sông nhỏ giữa đồng lúa và núi đá lúc mặt trời lặn', 'A small river between rice fields and limestone hills at sunset'] },
  { file: 'image13.png', slug: 'tea-rows', focal: [35, 50], mark: 'small vertical mark, right edge',
    alt: ['Người hái chè đội nón giữa những hàng chè xanh', 'Tea pickers in conical hats between green tea rows'] },
  { file: 'image14.png', slug: 'lotus-hat', focal: [50, 35], mark: null,
    alt: ['Chiếc nón lá giữa đầm sen', 'A conical hat among lotus leaves and flowers'] },
  { file: 'image15.png', slug: 'seedlings', focal: [50, 40], mark: null,
    alt: ['Người nông dân gánh mạ, nước nhỏ giọt trong nắng', 'A farmer carrying bundles of rice seedlings, water dripping in the sun'] },
  { file: 'image16.png', slug: 'tea-hills-mist', focal: [50, 50], mark: null,
    alt: ['Đồi chè trong sương sớm', 'Tea hills in morning mist'] },
  { file: 'image17.png', slug: 'village-tree', focal: [45, 60], mark: '"Hoang Cuong Photography", top left',
    alt: ['Cây đa lớn, đường làng phơi rơm và người đạp xe trong nắng sớm', 'A great banyan tree, a village road with drying straw and cyclists in early light'] },
  { file: 'image18.png', slug: 'threshing', focal: [55, 60], mark: null,
    alt: ['Hai người đập lúa trên ruộng bậc thang, núi phía xa', 'Two people threshing rice on terraced fields, mountains behind'] },
  { file: 'image19.png', slug: 'flower-hill-pickers', focal: [50, 65], mark: '"DanielKordan.com", bottom right',
    alt: ['Ba người gùi hoa đi giữa đồi hoa và ruộng bậc thang trong sương', 'Three people with baskets walking through flowering hills and terraces in mist'] },
  { file: 'image20.png', slug: 'seedling-bundle', focal: [50, 45], mark: 'Tuổi Trẻ logo, bottom right',
    alt: ['Người nông dân đội nón cầm bó mạ xanh', 'A farmer in a conical hat holding a bundle of green seedlings'] },
  { file: 'image21.png', slug: 'grain-jars', focal: [50, 40], mark: null,
    alt: ['Người sàng hạt trên nong tre giữa những chum sành', 'A person sifting grain on a bamboo tray among clay jars'] },
  { file: 'image22.png', slug: 'green-field-aerial', focal: [50, 50], mark: '"DanielKordan.com", bottom right',
    alt: ['Nhìn từ trên cao: người làm đồng giữa ruộng xanh mướt', 'Seen from above: farm workers in a lush green field'] },
];

const hex = ({ r, g, b }) => `#${[r, g, b].map((v) => v.toString(16).padStart(2, '0')).join('')}`;

if (!existsSync(SRC)) {
  console.log(`no mood folder at ${SRC}; nothing built (the app uses the licensed photos)`);
  process.exit(0);
}
await rm(OUT, { recursive: true, force: true });
await mkdir(OUT, { recursive: true });

const media = {};
for (const m of MOOD) {
  const file = path.join(SRC, m.file);
  if (!existsSync(file)) throw new Error(`missing ${file}`);
  const { width, height } = await sharp(file).metadata();
  const widths = [...new Set([...WIDTHS.filter((w) => w < width), Math.min(width, WIDTHS.at(-1))])].sort((a, b) => a - b);
  const slug = `mood-${m.slug}`;
  const sources = [];
  for (const w of widths) {
    const name = `${slug}-${w}`;
    await sharp(file).resize({ width: w }).avif({ quality: 55, effort: 4 }).toFile(path.join(OUT, `${name}.avif`));
    await sharp(file).resize({ width: w }).webp({ quality: 80, effort: 5 }).toFile(path.join(OUT, `${name}.webp`));
    sources.push({ w, avif: `media/mood/${name}.avif`, webp: `media/mood/${name}.webp` });
  }
  const lqip = await sharp(file).resize({ width: 24 }).blur(1.2).webp({ quality: 40 }).toBuffer();
  const { dominant } = await sharp(file).resize({ width: 256 }).toBuffer().then((b) => sharp(b).stats());
  media[slug] = {
    kind: 'mood', width, height, sources,
    placeholder: `data:image/webp;base64,${lqip.toString('base64')}`,
    dominant: hex(dominant),
    focal: { x: m.focal[0], y: m.focal[1] },
    alt: { vi: m.alt[0], en: m.alt[1] },
    caption: { vi: m.alt[0], en: m.alt[1] },
    credit: null, license: null, license_url: null, source_url: null,
    geography: { vi: 'Không rõ địa điểm', en: 'Place not recorded' },
    is_study_area: false,
    use: 'section',
    mark: m.mark,
  };
  console.log(slug, `${width}x${height}`, widths.join(','));
}
await writeFile(JSON_OUT, `${JSON.stringify(media, null, 1)}\n`);
console.log(`media.mood.json: ${Object.keys(media).length} entries`);
