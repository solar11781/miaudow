import type { SVGProps } from 'react';

// One line-icon set: 24 px grid, 1.7 stroke, round caps. Drawn for this app (rice, canal, seal, buffalo-free).
const PATHS = {
  arrowUpRight: 'M7 17 17 7M9 7h8v8',
  arrowRight: 'M5 12h14M13 6l6 6-6 6',
  arrowLeft: 'M19 12H5M11 6l-6 6 6 6',
  check: 'M5 12.5 9.5 17 19 7',
  close: 'M6 6l12 12M18 6 6 18',
  menu: 'M4 7h16M4 12h16M4 17h16',
  globe: 'M12 3a9 9 0 1 0 0 18 9 9 0 0 0 0-18Zm-9 9h18M12 3c2.5 2.6 3.8 5.6 3.8 9s-1.3 6.4-3.8 9c-2.5-2.6-3.8-5.6-3.8-9S9.5 5.6 12 3Z',
  leaf: 'M5 19C5 10 11 4 20 4c0 9-6 15-15 15ZM5 19l8-8',
  sprout: 'M12 20v-8M12 12c0-4-3-6-7-6 0 4 3 6 7 6ZM12 14c0-4 3-6 7-6 0 4-3 6-7 6ZM5 20h14',
  drop: 'M12 3c3.5 4.5 6 7.7 6 11a6 6 0 0 1-12 0c0-3.3 2.5-6.5 6-11Z',
  coin: 'M12 3a9 9 0 1 0 0 18 9 9 0 0 0 0-18ZM9 9.5c0-1 1.2-1.8 3-1.8s3 .7 3 1.9c0 2.6-6 1.2-6 4.2 0 1.1 1.3 1.9 3 1.9s3-.8 3-1.8M12 6v1.7M12 16.3V18',
  shield: 'M12 3 4 6v6c0 4.4 3.4 7.9 8 9 4.6-1.1 8-4.6 8-9V6l-8-3ZM8.5 12.5l2.4 2.4 4.6-4.9',
  sun: 'M12 7a5 5 0 1 0 0 10 5 5 0 0 0 0-10ZM12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4',
  rain: 'M7 15a4 4 0 0 1 .5-8A6 6 0 0 1 19 9a3 3 0 0 1-1 6H7ZM8 18l-1 3M12 18l-1 3M16 18l-1 3',
  snow: 'M12 3v18M4.2 7.5l15.6 9M4.2 16.5l15.6-9M9.5 4.5 12 7l2.5-2.5M9.5 19.5 12 17l2.5 2.5',
  crack: 'M3 20h18M5 20l3-6 3 3 2-5 3 4 3-3M7 8l2-3 2 2 2-3',
  calendar: 'M5 5h14v15H5zM5 9h14M9 3v4M15 3v4',
  share: 'M18 8a3 3 0 1 0 0-6 3 3 0 0 0 0 6ZM6 15a3 3 0 1 0 0-6 3 3 0 0 0 0 6ZM18 22a3 3 0 1 0 0-6 3 3 0 0 0 0 6ZM8.6 13.5l6.8 4M15.4 6.5l-6.8 4',
  question: 'M12 21a9 9 0 1 0 0-18 9 9 0 0 0 0 18ZM9.5 9.3a2.6 2.6 0 0 1 5 .9c0 1.7-2.5 2.2-2.5 3.8M12 17h.01',
  alert: 'M12 4 2.8 19.5h18.4L12 4ZM12 10v4.2M12 17h.01',
  play: 'M8 5v14l11-7L8 5Z',
  pause: 'M7 5h3.5v14H7zM13.5 5H17v14h-3.5z',
  rotateL: 'M4 12a8 8 0 1 0 2.5-5.8M4 4v4.5h4.5',
  rotateR: 'M20 12a8 8 0 1 1-2.5-5.8M20 4v4.5h-4.5',
  reset: 'M12 3v3M12 18v3M3 12h3M18 12h3M12 8a4 4 0 1 0 0 8 4 4 0 0 0 0-8Z',
  layers: 'M12 3 3 8l9 5 9-5-9-5ZM3 13l9 5 9-5M3 17.5l9 5 9-5',
  book: 'M4 5.5A2.5 2.5 0 0 1 6.5 3H20v15H6.5A2.5 2.5 0 0 0 4 20.5v-15ZM4 20.5A2.5 2.5 0 0 0 6.5 23H20',
  satellite: 'M13 7 17 3l4 4-4 4M7 13l-4 4 4 4 4-4M9 9l6 6M8.5 15.5a5 5 0 0 1-5-5M13.5 9.5l-4 4',
  grid: 'M4 4h16v16H4zM4 10h16M4 15h16M10 4v16M15 4v16',
  scale: 'M12 3v18M7 21h10M5 7h14M5 7l-2.5 6a2.5 2.5 0 0 0 5 0L5 7ZM19 7l-2.5 6a2.5 2.5 0 0 0 5 0L19 7Z',
  chart: 'M4 20V4M4 20h16M8 16l3.5-4.5 3 2.5L20 7',
  user: 'M12 12a4 4 0 1 0 0-8 4 4 0 0 0 0 8ZM4.5 21a7.5 7.5 0 0 1 15 0',
  spark: 'M12 3v4M12 17v4M3 12h4M17 12h4M6 6l2.5 2.5M15.5 15.5 18 18M6 18l2.5-2.5M15.5 8.5 18 6',
  search: 'M11 4a7 7 0 1 0 0 14 7 7 0 0 0 0-14ZM20 20l-4-4',
  hat: 'M2.5 15.5 12 5l9.5 10.5c-3 1.6-6.2 2.4-9.5 2.4s-6.5-.8-9.5-2.4ZM8 18v1.5M16 18v1.5',
  canal: 'M3 6h18M3 18h18M4 12c2.2-2 4.4-2 6.6 0s4.4 2 6.6 0 2.4-1.2 2.8-1',
  terrain: 'M3 19 9 9l4 6 3-4 5 8H3Z',
  moon: 'M20 14.5A8 8 0 0 1 9.5 4a8 8 0 1 0 10.5 10.5Z',
  feather: 'M20 4c-6 0-11 4-12 11l-3 5M8 15h6M10 11h7',
} as const;

export type IconName = keyof typeof PATHS;

export function Icon({ name, size = 20, strokeWidth = 1.7, ...rest }: { name: IconName; size?: number; strokeWidth?: number } & SVGProps<SVGSVGElement>) {
  const filled = name === 'play' || name === 'pause';
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" aria-hidden="true" focusable="false"
      fill={filled ? 'currentColor' : 'none'} stroke={filled ? 'none' : 'currentColor'}
      strokeWidth={strokeWidth} strokeLinecap="round" strokeLinejoin="round" {...rest}>
      <path d={PATHS[name]} />
    </svg>
  );
}

/** The source seal: a small red chop with a rice ear, the app's signature mark next to every sourced number. */
export function SealGlyph({ size = 12 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 12 12" aria-hidden="true" focusable="false">
      <path d="M6 10.6V6.2M6 6.2c.1-1.9.7-3.4 1.9-4.8M6.1 6.3c-1 .2-1.9.9-2.5 2M6.2 8.1c1 .2 1.8.8 2.3 1.8" stroke="currentColor" strokeWidth="1.3" fill="none" strokeLinecap="round" />
      <ellipse cx="8.2" cy="2.7" rx=".8" ry="1.3" transform="rotate(30 8.2 2.7)" fill="currentColor" />
    </svg>
  );
}
