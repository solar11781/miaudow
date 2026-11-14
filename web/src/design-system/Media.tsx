import { useState } from 'react';
import { media } from '../data/media';
import { usePick, useT } from '../app/settings';
import s from './Media.module.css';

interface Props {
  slug: string;
  /** A taller picture for phones (art direction); only one of the two is downloaded. */
  narrow?: string;
  /** CSS sizes attribute; keeps phones from downloading desktop widths. */
  sizes: string;
  priority?: boolean;
  className?: string;
  /** Decorative images get empty alt text; meaningful ones carry their description. */
  decorative?: boolean;
  /** Kept for callers; pictures carry no caption or credit on top. Credits live in the footer list. */
  label?: 'overlay' | 'none';
  /** Slow drift for hero images; switched off by the caller under reduced motion or when paused. */
  drift?: boolean;
}

const set = (slug: string, kind: 'avif' | 'webp') => media(slug).sources.map((x) => `${x[kind]} ${x.w}w`).join(', ');

/** AVIF/WebP picture with a blurred placeholder and the image's own focal point. No text on the picture. */
export function Media({ slug, narrow, sizes, priority, className, decorative, drift }: Props) {
  const pick = usePick();
  const t = useT();
  const m = media(slug);
  const [loaded, setLoaded] = useState(false);
  const pos = `${m.focal.x}% ${m.focal.y}%`;
  const fallback = m.sources[m.sources.length - 1]?.webp;
  const illustration = m.kind === 'illustration';
  const phone = '(max-width: 700px)';
  return (
    <span className={[s.frame, className].filter(Boolean).join(' ')} style={{ backgroundColor: m.dominant }}>
      <img className={s.ph} src={m.placeholder} alt="" aria-hidden="true" style={{ objectPosition: pos }} />
      <picture>
        {narrow && <source media={phone} type="image/avif" srcSet={set(narrow, 'avif')} sizes="100vw" />}
        {narrow && <source media={phone} type="image/webp" srcSet={set(narrow, 'webp')} sizes="100vw" />}
        <source type="image/avif" srcSet={set(slug, 'avif')} sizes={sizes} />
        <source type="image/webp" srcSet={set(slug, 'webp')} sizes={sizes} />
        <img
          className={[s.img, loaded ? s.on : '', drift ? s.drift : ''].join(' ')}
          src={fallback}
          width={m.width}
          height={m.height}
          alt={decorative ? '' : `${pick(m.alt)}${illustration ? ` (${t.media.illustration})` : ''}`}
          loading={priority ? 'eager' : 'lazy'}
          decoding="async"
          fetchPriority={priority ? 'high' : 'auto'}
          onLoad={() => setLoaded(true)}
          ref={(el) => { if (el?.complete && el.naturalWidth && !loaded) setLoaded(true); }}
          style={{ objectPosition: pos, transformOrigin: pos }}
        />
      </picture>
    </span>
  );
}
