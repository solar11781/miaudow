import { useState } from 'react';
import { media } from '../data/media';
import { usePick, useT } from '../app/settings';
import s from './Media.module.css';

interface Props {
  slug: string;
  /** CSS sizes attribute; keeps phones from downloading desktop widths. */
  sizes: string;
  priority?: boolean;
  className?: string;
  /** Decorative images get empty alt text; meaningful ones carry their description. */
  decorative?: boolean;
  /** Where the label sits: a photo shows its credit, an illustration always says it is one (never hidden). */
  label?: 'overlay' | 'none';
  /** Slow drift for hero images; switched off by the caller under reduced motion or when paused. */
  drift?: boolean;
}

/** AVIF/WebP picture with a blurred placeholder, the image's own focal point and an honest label. */
export function Media({ slug, sizes, priority, className, decorative, label = 'overlay', drift }: Props) {
  const pick = usePick();
  const t = useT();
  const m = media(slug);
  const [loaded, setLoaded] = useState(false);
  const pos = `${m.focal.x}% ${m.focal.y}%`;
  const avif = m.sources.map((x) => `${x.avif} ${x.w}w`).join(', ');
  const webp = m.sources.map((x) => `${x.webp} ${x.w}w`).join(', ');
  const fallback = m.sources[m.sources.length - 1]?.webp;
  const illustration = m.kind === 'illustration';
  return (
    <span className={[s.frame, className].filter(Boolean).join(' ')} style={{ backgroundColor: m.dominant }}>
      <img className={s.ph} src={m.placeholder} alt="" aria-hidden="true" style={{ objectPosition: pos }} />
      <picture>
        <source type="image/avif" srcSet={avif} sizes={sizes} />
        <source type="image/webp" srcSet={webp} sizes={sizes} />
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
          ref={(el) => {
            if (el?.complete && el.naturalWidth && !loaded) setLoaded(true);
          }}
          style={{ objectPosition: pos, transformOrigin: pos }}
        />
      </picture>
      {label === 'overlay' && (
        <span className={[s.tag, illustration ? s.tagArt : ''].join(' ')}>
          {illustration ? t.media.illustration : m.credit ? pick(m.credit) : t.media.photo}
        </span>
      )}
    </span>
  );
}
