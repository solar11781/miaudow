import type { CSSProperties, ElementType, ReactNode } from 'react';

/**
 * A plain wrapper. It used to fade every block up on scroll, which reads as a template; the pages now choose one
 * authored GSAP moment each (src/motion). Kept so callers keep their markup; `delay` is accepted and ignored.
 */
export function Reveal({ as: Tag = 'div', children, className, style, id }: {
  as?: ElementType; children: ReactNode; className?: string; delay?: number; id?: string; style?: CSSProperties;
}) {
  return (
    <Tag className={className} style={style} id={id}>
      {children}
    </Tag>
  );
}
