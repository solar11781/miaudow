import { useEffect, useRef, type CSSProperties, type ElementType, type ReactNode } from 'react';
import { useSettings } from '../app/settings';

/**
 * Fades content up as it scrolls into view. Content already in the first screen is never hidden, so the first frame
 * is complete (thumbnails, slow phones, screen readers). Off in lite mode and under reduced motion.
 */
export function Reveal({
  as: Tag = 'div',
  children,
  className,
  delay = 0,
  style,
  ...rest
}: {
  as?: ElementType;
  children: ReactNode;
  className?: string;
  delay?: number;
  id?: string;
  style?: CSSProperties;
}) {
  const ref = useRef<HTMLElement>(null);
  const { calm } = useSettings();

  useEffect(() => {
    const el = ref.current;
    if (!el || calm || !('IntersectionObserver' in window)) return;
    if (el.getBoundingClientRect().top < window.innerHeight * 0.92) return;
    el.dataset.pre = 'true';
    const io = new IntersectionObserver(
      (entries) =>
        entries.forEach((e) => {
          if (!e.isIntersecting) return;
          el.dataset.pre = 'false';
          io.disconnect();
        }),
      { threshold: 0.12, rootMargin: '0px 0px -6% 0px' },
    );
    io.observe(el);
    return () => io.disconnect();
  }, [calm]);

  return (
    <Tag
      ref={ref}
      className={['reveal', className].filter(Boolean).join(' ')}
      style={delay ? { ...style, transitionDelay: `${delay}ms` } : style}
      {...rest}
    >
      {children}
    </Tag>
  );
}
