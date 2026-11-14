import type { Value, WaterFact } from '../types';

// one number in the API's notation (D-170: English, comma for thousands, dot for decimals), alone or as low-high
const NUMBER = String.raw`\d{1,3}(?:,\d{3})*(?:\.\d+)?`;
const RANGE = new RegExp(`^(${NUMBER})(?:-(${NUMBER}))?$`);
type End = { n: number; text: string };
const end = (text: string): End => ({ n: Number(text.replace(/,/g, '')), text });

/** Both ends of an API value string such as "2,000" or "6,500-7,500"; null for anything else. */
function ends(value: string): [End, End] | null {
  const m = RANGE.exec(value);
  if (!m?.[1]) return null;
  const low = end(m[1]);
  const high = m[2] ? end(m[2]) : low;
  return low.n <= high.n ? [low, high] : null;
}

/** [low, high] of an API value string such as "2,000" or "6,500-7,500"; null for anything else. */
export function parseRange(value: string): [number, number] | null {
  const e = ends(value);
  return e && [e[0].n, e[1].n];
}

/** The lowest to the highest of a crop's TCVN 8641 rows (D-175, "by region": D-68), written with the rows' own number
 * strings and carrying all their source ids; FAO rows stay out (D-64). Null when the crop has no TCVN row, a row
 * cannot be read or the rows differ in unit. */
export function tcvnRange(facts: WaterFact[]): Value | null {
  const rows = facts.flatMap((w) => (w.measure === 'to_apply' && w.value ? [w.value] : []));
  const first = rows[0];
  if (!first || rows.some((v) => v.unit.en !== first.unit.en)) return null;
  let low: End | null = null;
  let high: End | null = null;
  for (const v of rows) {
    const e = ends(v.value);
    if (!e) return null;
    if (!low || e[0].n < low.n) low = e[0];
    if (!high || e[1].n > high.n) high = e[1];
  }
  if (!low || !high) return null;
  return {
    value: low.n === high.n ? low.text : `${low.text}-${high.text}`,
    unit: first.unit,
    source_ids: [...new Set(rows.flatMap((v) => v.source_ids))],
  };
}
