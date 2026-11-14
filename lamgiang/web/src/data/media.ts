// The image library (web/pipeline/build_media.mjs → generated/media.json; full rights record in
// assets/photos/PHOTO_MANIFEST.json and assets/ASSET_MANIFEST.json). Three kinds never mix:
// - photo: a real photograph with creator, licence and place as the source states them;
// - illustration: AI-generated concept art, never captioned as Nghệ An;
// - mood: photographs the team supplied without a recorded author or licence (pipeline/build_mood.mjs). They exist
//   only on a machine that built them (git-ignored) and are never captioned with a place.
import mediaJson from './generated/media.json';
import type { Bilingual } from '../domain/provenance';

export interface MediaAsset {
  kind: 'photo' | 'illustration' | 'mood';
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

const mood = Object.values(
  import.meta.glob<Record<string, MediaAsset>>('./generated/media.mood.json', { eager: true, import: 'default' }),
)[0] ?? {};

export const MEDIA: Record<string, MediaAsset> = { ...(mediaJson as unknown as Record<string, MediaAsset>), ...mood };
export type MediaSlug = keyof typeof MEDIA & string;

/** True when the team's mood photographs were built on this machine. */
export const HAS_MOOD = Object.keys(mood).length > 0;

export function media(slug: string): MediaAsset {
  const m = MEDIA[slug];
  if (!m) throw new Error(`unknown media slug ${slug}`);
  return m;
}

/** Real photographs, in manifest order, for the credits list. */
export const PHOTO_CREDITS = Object.entries(MEDIA).filter(([, m]) => m.kind === 'photo');
