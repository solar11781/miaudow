import { useCallback } from 'react';
import type { To } from 'react-router-dom';
import { useSettings, type Lang } from './settings';

// D-174: the English path of every page, segment by segment; the Vietnamese paths stay the main ones
export const EN_SEGMENT: Record<string, string> = {
  'nong-dan': 'farmer',
  ruong: 'field',
  nam: 'years',
  'uu-tien': 'priority',
  'phuong-an': 'plans',
  'can-bo': 'officer',
  'khoa-hoc': 'science',
  'phuong-phap': 'method',
  'dai-quan-sat': 'observatory',
  'bang-chung': 'evidence',
  'tro-ly': 'assistant',
  'dang-nhap': 'sign-in',
  'da-luu': 'saved',
};
const VI_SEGMENT = Object.fromEntries(Object.entries(EN_SEGMENT).map(([vi, en]) => [en, vi]));
export const EN_HOME = '/home';

/** The same page's path in `lang`; a path already in that language, or one not in the map, stays as it is. */
export function pathFor(path: string, lang: Lang): string {
  if (path === '/' || path === EN_HOME) return lang === 'en' ? EN_HOME : '/';
  const map = lang === 'en' ? EN_SEGMENT : VI_SEGMENT;
  return path
    .split('/')
    .map((seg) => map[seg] ?? seg)
    .join('/');
}

export const isEnglishPath = (path: string) => path === EN_HOME || (path.split('/')[1] ?? '') in VI_SEGMENT;

/** A link target in `lang`; only the path changes, so the answers after "?" stay exactly as they are. */
export function localTo(to: To, lang: Lang): To {
  if (typeof to !== 'string') return to.pathname === undefined ? to : { ...to, pathname: pathFor(to.pathname, lang) };
  const at = to.indexOf('?');
  return at < 0 ? pathFor(to, lang) : `${pathFor(to.slice(0, at), lang)}${to.slice(at)}`;
}

/** Maps a link target to the current language's path (nav, footer, step links and every ButtonLink). */
export function useLocalTo() {
  const { lang } = useSettings();
  return useCallback((to: To) => localTo(to, lang), [lang]);
}
