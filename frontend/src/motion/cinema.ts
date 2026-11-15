// The one place that loads GSAP (gsap 3.15.0, @gsap/react 2.1.2; GSAP's standard no-charge licence, D-043).
// Every animation is added on top of a finished page: the CSS shows the final state, GSAP animates *from* elsewhere,
// and nothing runs in lite mode or under prefers-reduced-motion (H1, D-155). gsap.matchMedia reverts the animations
// when the system setting changes; useGSAP reverts them when the component unmounts.
import { useGSAP } from '@gsap/react';
import { gsap } from 'gsap';
import { ScrollTrigger } from 'gsap/ScrollTrigger';
import { SplitText } from 'gsap/SplitText';
import type { RefObject } from 'react';
import { useSettings } from '../app/settings';

gsap.registerPlugin(useGSAP, ScrollTrigger, SplitText);

/** Three characters of motion: heavy for the cinema, calm for transitions, light for the tools. */
export const EASE = { heavy: 'expo.out', calm: 'power3.inOut', ui: 'power2.out' } as const;

/**
 * Runs `build` inside the scope when motion is allowed (what it returns is ignored). Desktop-only parts can check
 * `wide` (min-width 900 px), which is re-evaluated when the window crosses it.
 */
export function useCinema(
  scope: RefObject<HTMLElement | null>,
  build: (ctx: { wide: boolean }) => unknown,
  dependencies: unknown[] = [],
) {
  const { calm } = useSettings();
  useGSAP(
    () => {
      if (calm) return;
      const mm = gsap.matchMedia();
      mm.add(
        {
          wide: '(min-width: 900px) and (prefers-reduced-motion: no-preference)',
          narrow: '(max-width: 899.98px) and (prefers-reduced-motion: no-preference)',
        },
        (ctx) => {
          build({ wide: Boolean(ctx.conditions?.wide) });
        },
      );
      return () => mm.revert();
    },
    { scope, dependencies: [calm, ...dependencies], revertOnUpdate: true },
  );
}

/** A heading that rises line by line out of a mask, once. For the one title of a page, never for body text. */
export function riseLines(el: Element, delay = 0) {
  return SplitText.create(el, {
    type: 'lines',
    mask: 'lines',
    autoSplit: true,
    onSplit: (self) => {
      // Vietnamese stacks marks above and below the letters (ộ, ụ, ữ): give each mask room so none is clipped.
      self.masks.forEach((m) => {
        (m as HTMLElement).style.padding = '.2em 0 .16em';
        (m as HTMLElement).style.margin = '-.2em 0 -.16em';
      });
      return gsap.from(self.lines, { yPercent: 120, duration: 1.25, ease: EASE.heavy, stagger: 0.09, delay });
    },
  });
}

export { gsap, ScrollTrigger };

/**
 * Section headings lift into view and marked groups (`data-stagger`) come in one after another, each when it first
 * scrolls into view. Only the h2 of a section and the children of a marked group move; body text never does.
 */
export function revealSections(scope: Element) {
  // Section headings are revealed whole (a curtain lifting from the top), never split: many hold live text, such as
  // the chosen year, and must stay React's own DOM.
  scope.querySelectorAll('h2:not([data-rise])').forEach((h) => {
    gsap.fromTo(
      h,
      { clipPath: 'inset(0% 0% 100% 0%)', y: 28 },
      {
        clipPath: 'inset(-25% -5% -25% -5%)',
        y: 0,
        duration: 1.1,
        ease: EASE.heavy,
        clearProps: 'clipPath,transform',
        scrollTrigger: { trigger: h, start: 'top 88%', once: true },
      },
    );
  });
  scope.querySelectorAll('[data-stagger]').forEach((group) => {
    gsap.from(group.children, {
      opacity: 0,
      y: 28,
      duration: 0.9,
      ease: EASE.heavy,
      stagger: 0.08,
      scrollTrigger: { trigger: group, start: 'top 88%', once: true },
    });
  });
  scope.querySelectorAll('[data-bars] rect[data-bar]').forEach((bar, i) => {
    gsap.from(bar, {
      scaleY: 0,
      transformOrigin: '50% 100%',
      duration: 0.9,
      ease: EASE.heavy,
      delay: (i % 40) * 0.025,
      scrollTrigger: { trigger: bar.closest('[data-bars]') ?? bar, start: 'top 90%', once: true },
    });
  });
}

/** Section reveals for a whole page (headings, marked groups, chart bars), see `revealSections`. */
export function usePageReveals(ref: RefObject<HTMLElement | null>, dependencies: unknown[] = []) {
  useCinema(
    ref,
    () => {
      if (ref.current) revealSections(ref.current);
    },
    dependencies,
  );
}
