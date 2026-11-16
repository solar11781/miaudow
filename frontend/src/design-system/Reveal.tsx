import type { CSSProperties, ReactNode } from 'react';

/**
 * A plain wrapper. It used to fade every block up on scroll, which reads as a template; the pages now choose one
 * authored GSAP moment each (src/motion). Kept so callers keep their markup.
 */
export function Reveal({
  children,
  className,
  style,
}: {
  children: ReactNode;
  className?: string;
  style?: CSSProperties;
}) {
  return (
    <div className={className} style={style}>
      {children}
    </div>
  );
}
