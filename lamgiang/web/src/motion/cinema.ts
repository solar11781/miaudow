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
        { wide: '(min-width: 900px) and (prefers-reduced-motion: no-preference)', narrow: '(max-width: 899.98px) and (prefers-reduced-motion: no-preference)' },
        (ctx) => { build({ wide: Boolean(ctx.conditions?.wide) }); },
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
