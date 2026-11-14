import type { Lang } from '../types';

/** An API Value string (English notation, already rounded) as shown in `lang`: Vietnamese swaps the separators, so
 * "30,799" reads "30.799" and "0.42" reads "0,42". The digits never change. */
export const displayValue = (value: string, lang: Lang) =>
  lang === 'vi' ? value.replace(/[.,]/g, (c) => (c === ',' ? '.' : ',')) : value;

/** A unit as written on screen: cubic metres with the superscript. */
export const displayUnit = (unit: string) => unit.replace(/\bm3\b/g, 'm³');
