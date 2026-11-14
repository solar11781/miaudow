import { useLayoutEffect, useRef, useState } from 'react';

/** Width of an element in CSS pixels, kept up to date. Charts draw in this width so one SVG unit is one pixel and
 * their 17 px labels stay 17 px on a phone (UI-UX-SPEC H6) instead of shrinking with a fixed viewBox. The width is
 * rounded down: a CSS width of 100% then only scales the drawing up, never below 17 px (rounding up gave 16.99 px). */
export function useWidth<T extends HTMLElement>(fallback = 640) {
  const ref = useRef<T>(null);
  const [width, setWidth] = useState(fallback);
  useLayoutEffect(() => {
    const el = ref.current;
    if (!el) return;
    const first = Math.floor(el.getBoundingClientRect().width);
    if (first > 0) setWidth(first);
    if (typeof ResizeObserver === 'undefined') return;
    const ro = new ResizeObserver(([entry]) => {
      const w = Math.floor(entry?.contentRect.width ?? 0);
      if (w > 0) setWidth(w);
    });
    ro.observe(el);
    return () => ro.disconnect();
  }, []);
  return [ref, width] as const;
}

/** Every how many years an axis label fits, given the pixel width of one year (labels are about 46 px wide). */
export function yearLabelStep(pxPerYear: number): number {
  for (const step of [1, 2, 5, 10]) if (pxPerYear * step >= 52) return step;
  return 15;
}
