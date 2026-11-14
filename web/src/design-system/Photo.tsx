import { useState } from 'react';
import { photoAsset, PHOTOS, type PhotoSlug } from '../data/photos';
import { usePick } from '../app/settings';
import s from './Photo.module.css';

interface Props {
  slug: PhotoSlug;
  /** CSS sizes attribute; keeps phones from downloading desktop widths. */
  sizes: string;
  priority?: boolean;
  className?: string;
  /** Override the stored focal point (object-position). */
  focus?: string;
  /** Decorative photos get empty alt text; meaningful ones carry the caption. */
  decorative?: boolean;
}

/** Responsive WebP with a blurred placeholder that fades into the sharp image (no layout shift). */
export function Photo({ slug, sizes, priority, className, focus, decorative }: Props) {
  const pick = usePick();
  const meta = PHOTOS[slug];
  const asset = photoAsset(slug);
  const [loaded, setLoaded] = useState(false);
  const srcSet = asset.sources.map((x) => `${x.src} ${x.w}w`).join(', ');
  const fallback = asset.sources[asset.sources.length - 1]?.src;
  return (
    <span className={[s.frame, className].filter(Boolean).join(' ')} style={{ backgroundColor: asset.dominant }}>
      <img className={s.ph} src={asset.placeholder} alt="" aria-hidden="true" style={{ objectPosition: focus ?? meta.focus }} />
      <img
        className={[s.img, loaded ? s.on : ''].join(' ')}
        src={fallback}
        srcSet={srcSet}
        sizes={sizes}
        width={asset.width}
        height={asset.height}
        alt={decorative ? '' : pick(meta.alt)}
        loading={priority ? 'eager' : 'lazy'}
        decoding="async"
        fetchPriority={priority ? 'high' : 'auto'}
        onLoad={() => setLoaded(true)}
        ref={(el) => { if (el?.complete && el.naturalWidth && !loaded) setLoaded(true); }}
        style={{ objectPosition: focus ?? meta.focus }}
      />
    </span>
  );
}
