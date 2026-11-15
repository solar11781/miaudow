// The image library (web/pipeline/build_media.mjs → generated/media.json; full rights record in
// assets/photos/PHOTO_MANIFEST.json and assets/ASSET_MANIFEST.json). Two kinds never mix:
// - photo: a real photograph with creator, licence and place as the source states them;
// - illustration: AI-generated concept art, never captioned as Nghệ An.
import mediaJson from './generated/media.json';
import type { Bilingual } from '../domain/provenance';

export interface MediaAsset {
  kind: 'photo' | 'illustration';
  width: number;
  height: number;
  sources: { w: number; avif: string; webp: string }[];
  placeholder: string;
  dominant: string;
  focal: { x: number; y: number };
  alt: Bilingual;
  caption: Bilingual;
  credit: Bilingual | null;
  license: string | null;
  license_url: string | null;
  source_url: string | null;
  geography: Bilingual;
  is_study_area: boolean;
  use: 'hero' | 'section' | 'card' | 'avoid';
}

export const MEDIA = mediaJson as unknown as Record<string, MediaAsset>;

export function media(slug: string): MediaAsset {
  const m = MEDIA[slug];
  if (!m) throw new Error(`unknown media slug ${slug}`);
  return m;
}

/** Real photographs, in manifest order, for the credits list. */
export const PHOTO_CREDITS = Object.entries(MEDIA).filter(([, m]) => m.kind === 'photo');
