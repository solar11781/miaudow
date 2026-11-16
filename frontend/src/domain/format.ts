import type { Lang } from '../types';

/** An API Value string (English notation, already rounded) as shown in `lang` (D-170): Vietnamese swaps the
 * separators, so "30,799" reads "30.799" and "0.42" reads "0,42". The digits never change. */
export const displayValue = (value: string, lang: Lang) =>
  lang === 'vi' ? value.replace(/[.,]/g, (c) => (c === ',' ? '.' : ',')) : value;

/** A unit or an API text as written on screen (D-170): square and cubic metres with the superscript. */
export const displayUnit = (text: string) => text.replace(/\bm([23])\b/g, (_, p: string) => (p === '2' ? 'm²' : 'm³'));

/** A rulebook sentence as written on screen: `displayUnit`, and a size written without a thousands mark before a
 * square or cubic metre unit gets the mark of `lang` ("1000 m2" reads "1.000 m²" in Vietnamese, "1,000 m²" in English). */
export const displayMeasure = (text: string, lang: Lang) =>
  displayUnit(
    text.replace(/\b(\d{1,3})(\d{3})(?= m[23]\b)/g, (_, head: string, tail: string) =>
      displayValue(`${head},${tail}`, lang),
    ),
  );
/** A number with its unit as one text: a space between them, except a percent sign, which joins its number ("55%"). */
export const withUnit = (number: string, unit: string) => (unit === '%' ? `${number}%` : `${number} ${unit}`.trim());

/** A label such as a season name ("Lúa vụ Mùa", "Spring rice") inside a sentence, or a clause starting one. */
export const lowerFirst = (text: string) => text.charAt(0).toLowerCase() + text.slice(1);
export const upperFirst = (text: string) => text.charAt(0).toUpperCase() + text.slice(1);
