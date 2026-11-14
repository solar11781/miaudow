import { useRef, type ReactNode } from 'react';
import type { Shot } from '../data/art';
import { EASE, gsap, riseLines, useCinema } from '../motion/cinema';
import { Media } from './Media';
import s from './PhotoHead.module.css';

/** The opening band of a page: one photograph, the page title rising out of its mask, a short lead. */
export function PhotoHead({
  shot,
  id,
  title,
  lead,
  children,
}: {
  shot: Shot;
  id: string;
  title: string;
  lead?: string;
  children?: ReactNode;
}) {
  const root = useRef<HTMLElement>(null);
  useCinema(root, () => {
    const h = root.current?.querySelector('[data-rise]');
    if (h) riseLines(h, 0.1);
    gsap.from('[data-photo]', { scale: 1.12, duration: 2.2, ease: EASE.heavy });
  }, [title]);
  return (
    <header ref={root} className={`${s.head} surface-forest`}>
      <div className={s.photo} data-photo>
        <Media slug={shot.slug} narrow={shot.narrow} sizes="100vw" priority decorative />
      </div>
      <div className={`container ${s.inner}`}>
        {/* keyed by its text: SplitText rewrites the heading's DOM, so a new language mounts a fresh heading */}
        <h1 key={title} id={id} className={`display ${s.title}`} data-rise>
          {title}
        </h1>
        {lead && <p className={s.lead}>{lead}</p>}
        {children}
      </div>
    </header>
  );
}
