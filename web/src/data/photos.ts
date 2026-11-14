import type { Bilingual } from '../domain/provenance';
import { photoAssets, type PhotoAsset } from './index';

export type PhotoSlug =
  | 'ganh-ma' | 'dap-lua' | 'canh-dong-tren-cao' | 'dam-sen' | 'la-sen-non-la' | 'phoi-tuong'
  | 'doi-che' | 'bac-thang-song' | 'bac-thang-duong' | 'bac-thang-nang' | 'bac-thang-gat';

export interface PhotoMeta {
  slug: PhotoSlug;
  alt: Bilingual;
  caption: Bilingual;
  /** Where the scene belongs. Mountain terraces are never presented as Nghệ An. */
  region: 'lowland' | 'midland' | 'mountain';
  focus?: string;
}

// Captions describe what is visible; locations are not claimed because they are not known for every photo.
export const PHOTOS: Record<PhotoSlug, PhotoMeta> = {
  'ganh-ma': { slug: 'ganh-ma', region: 'lowland', focus: '52% 38%',
    alt: { vi: 'Người nông dân đội nón lá gánh những bó mạ còn nhỏ nước, phía sau là trâu và ruộng', en: 'A farmer in a conical hat carries bundles of rice seedlings still dripping water, a buffalo behind' },
    caption: { vi: 'Gánh mạ ra ruộng cấy', en: 'Carrying seedlings to transplant' } },
  'dap-lua': { slug: 'dap-lua', region: 'lowland', focus: '50% 30%',
    alt: { vi: 'Người nông dân đập lúa, hạt thóc bay trong nắng chiều', en: 'A farmer threshing rice, grains flying in the late sun' },
    caption: { vi: 'Mùa gặt, hạt thóc bay trong nắng', en: 'Harvest, grain in the evening light' } },
  'canh-dong-tren-cao': { slug: 'canh-dong-tren-cao', region: 'lowland', focus: '50% 50%',
    alt: { vi: 'Ảnh chụp từ trên cao: những người đội nón đi thành hàng dọc mương nước giữa cánh đồng xanh', en: 'Aerial view: people in conical hats walking in a line along a canal through a green field' },
    caption: { vi: 'Bờ mương giữa đồng xanh, nhìn từ trên cao', en: 'A canal through green fields, from above' } },
  'dam-sen': { slug: 'dam-sen', region: 'lowland', focus: '50% 50%',
    alt: { vi: 'Thuyền nhỏ giữa đầm sen, chụp từ trên cao', en: 'A small boat among lotus leaves, seen from above' },
    caption: { vi: 'Đầm sen', en: 'A lotus pond' } },
  'la-sen-non-la': { slug: 'la-sen-non-la', region: 'lowland', focus: '50% 40%',
    alt: { vi: 'Chiếc nón lá giữa những lá sen và hoa sen hồng', en: 'A conical hat among lotus leaves and pink lotus flowers' },
    caption: { vi: 'Nón lá giữa lá sen', en: 'A conical hat among lotus leaves' } },
  'phoi-tuong': { slug: 'phoi-tuong', region: 'lowland', focus: '45% 40%',
    alt: { vi: 'Người phụ nữ đội nón phơi đỗ tương trên nia giữa những chum tương', en: 'A woman in a conical hat dries soybeans on woven trays among sauce jars' },
    caption: { vi: 'Phơi đỗ làm tương, nghề truyền thống', en: 'Drying soybeans for tương, a traditional craft' } },
  'doi-che': { slug: 'doi-che', region: 'midland', focus: '50% 60%',
    alt: { vi: 'Đồi chè tròn nối tiếp nhau trong sương sớm', en: 'Rounded tea hills one after another in the morning mist' },
    caption: { vi: 'Đồi chè trung du trong sương sớm', en: 'Midland tea hills in morning mist' } },
  'bac-thang-song': { slug: 'bac-thang-song', region: 'mountain', focus: '50% 50%',
    alt: { vi: 'Ruộng bậc thang uốn theo dòng sông xanh, chụp từ trên cao', en: 'Terraces curving along a blue river, from above' },
    caption: { vi: 'Ruộng bậc thang ven sông, miền núi phía Bắc', en: 'Terraces by a river, northern mountains' } },
  'bac-thang-duong': { slug: 'bac-thang-duong', region: 'mountain', focus: '50% 50%',
    alt: { vi: 'Con đường đất uốn qua ruộng bậc thang và những mái nhà', en: 'A dirt road winding through terraces and village roofs' },
    caption: { vi: 'Đường làng qua ruộng bậc thang', en: 'A village road through terraces' } },
  'bac-thang-nang': { slug: 'bac-thang-nang', region: 'mountain', focus: '50% 60%',
    alt: { vi: 'Nắng sớm xuyên qua sương xuống thung lũng ruộng bậc thang', en: 'Morning light through mist over a terraced valley' },
    caption: { vi: 'Nắng sớm trên thung lũng bậc thang', en: 'Morning light on a terraced valley' } },
  'bac-thang-gat': { slug: 'bac-thang-gat', region: 'mountain', focus: '50% 55%',
    alt: { vi: 'Hai người tuốt lúa bên ruộng bậc thang vàng, núi xa phía sau', en: 'Two people threshing beside golden terraces, mountains behind' },
    caption: { vi: 'Mùa gặt trên ruộng bậc thang', en: 'Harvest on the terraces' } },
};

export const photoAsset = (slug: PhotoSlug): PhotoAsset => {
  const a = photoAssets[slug];
  if (!a) throw new Error(`missing photo asset ${slug}; run npm run photos`);
  return a;
};
