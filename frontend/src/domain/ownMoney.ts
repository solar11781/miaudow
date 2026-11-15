/** "Your price and costs" (UI-UX-SPEC section 12d, D-163), worked out in the browser; the farmer's numbers reach the
 * server only in a signed-in save (D-180): revenue = study yield (t/ha) x your price (đ/kg), which is thousand đ/ha; margin = revenue -
 * your cost (thousand đ/ha), only with a cost. Exact until one rounding at the end, half away from zero like the
 * engine's ROUND_HALF_UP (D-156); the results use the API's notation ("16,200"), so they display like its values. */

// routine cap (D-179, privacy review of PR #66): far above any real price in đ/kg or cost in thousand đ/ha, and a crafted
// link with huge values cannot freeze the page
const MAX_DIGITS = 9;
const WHOLE = new RegExp(`^[0-9]{1,${MAX_DIGITS}}$`);

/** The digits of a typed field (whole đồng or thousand đồng, 0 or more), null when empty, 'invalid' for anything else. */
export function readWhole(raw: string): string | null | 'invalid' {
  if (raw === '') return null;
  return WHOLE.test(raw) ? BigInt(raw).toString() : 'invalid';
}

// D-192: a cost typed in million đ/ha (one decimal comma or dot); the digit counts only bound the work, the limit is
// the thousand value's MAX_DIGITS
const MILLIONS = /^([0-9]{0,9})(?:[.,]([0-9]{0,9}))?$/;

/** The thousand-đồng digits of a cost typed in million đồng, rounded once to a whole thousand, half up (D-192). */
export function readMillions(raw: string): string | null | 'invalid' {
  if (raw === '') return null;
  const m = MILLIONS.exec(raw);
  const whole = m?.[1] ?? '';
  const decimals = m?.[2] ?? '';
  if (!m || whole + decimals === '') return 'invalid';
  // million = digits / 10^decimals, so thousand = digits x 1000 / 10^decimals, rounded half up
  const d = 10n ** BigInt(decimals.length);
  return readWhole(((BigInt(`${whole}${decimals}`) * 2000n + d) / (2n * d)).toString());
}

/** A kept cost in thousand đồng as million đồng, in the form a number field takes ("24.7"; D-192). */
export function millionsOf(thousands: string): string {
  const digits = thousands.padStart(4, '0');
  const fraction = digits.slice(-3).replace(/0+$/, '');
  return `${BigInt(digits.slice(0, -3)).toString()}${fraction && `.${fraction}`}`;
}

/** A number as numerator / 10^places, so the study's decimal yields stay exact. */
interface Exact {
  n: bigint;
  places: number;
}

function exactOf(value: string): Exact {
  const m = /^(\d+)(?:\.(\d+))?$/.exec(value.replaceAll(',', ''));
  if (!m) throw new Error(`not a number: ${value}`);
  const decimals = m[2] ?? '';
  return { n: BigInt(`${m[1]}${decimals}`), places: decimals.length };
}

const scale = (x: Exact, places: number) => x.n * 10n ** BigInt(places - x.places);

function add(a: Exact, b: Exact): Exact {
  const places = Math.max(a.places, b.places);
  return { n: scale(a, places) + scale(b, places), places };
}

function shown(x: Exact): string {
  const d = 10n ** BigInt(x.places);
  const abs = x.n < 0n ? -x.n : x.n;
  const whole = (2n * abs + d) / (2n * d);
  const sign = x.n < 0n && whole > 0n ? '-' : '';
  return sign + whole.toString().replace(/\B(?=(\d{3})+(?!\d))/g, ',');
}

export interface OwnEntry {
  /** Digits of your sale price, đ/kg. */
  price: string | null;
  /** Digits of your cost, thousand đ/ha. */
  cost: string | null;
}

export interface OwnResult {
  revenue: string | null;
  margin: string | null;
}

/** Per crop and for the whole year; a whole-year number only when every crop has what it needs (a partial sum would
 * read as the plan's total). */
export function ownMoney(yields: string[], entries: OwnEntry[]): { crops: OwnResult[]; total: OwnResult } {
  const parts = yields.map((y, i) => {
    const { price, cost } = entries[i] ?? { price: null, cost: null };
    if (price === null) return { revenue: null, margin: null };
    const yieldT = exactOf(y);
    const revenue = { n: yieldT.n * BigInt(price), places: yieldT.places };
    return { revenue, margin: cost === null ? null : add(revenue, { n: -BigInt(cost), places: 0 }) };
  });
  const sum = (xs: (Exact | null)[]) =>
    xs.length && xs.every((x): x is Exact => x !== null)
      ? shown(xs.reduce<Exact>((a, x) => add(a, x), { n: 0n, places: 0 }))
      : null;
  return {
    crops: parts.map((p) => ({
      revenue: p.revenue && shown(p.revenue),
      margin: p.margin && shown(p.margin),
    })),
    total: { revenue: sum(parts.map((p) => p.revenue)), margin: sum(parts.map((p) => p.margin)) },
  };
}
