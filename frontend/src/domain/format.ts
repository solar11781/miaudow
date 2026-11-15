import type { Lang } from '../types';

/** An API Value string (English notation, already rounded) as shown in `lang` (D-170): Vietnamese swaps the
 * separators, so "30,799" reads "30.799" and "0.42" reads "0,42". The digits never change. */
export const displayValue = (value: string, lang: Lang) =>
  lang === 'vi' ? value.replace(/[.,]/g, (c) => (c === ',' ? '.' : ',')) : value;

/** A unit or an API text as written on screen (D-170): square and cubic metres with the superscript. */
export const displayUnit = (text: string) => text.replace(/\bm([23])\b/g, (_, p: string) => (p === '2' ? 'm²' : 'm³'));

/** A label such as a season name ("Lúa vụ Mùa", "Spring rice") inside a sentence, or a clause starting one. */
export const lowerFirst = (text: string) => text.charAt(0).toLowerCase() + text.slice(1);
export const upperFirst = (text: string) => text.charAt(0).toUpperCase() + text.slice(1);
