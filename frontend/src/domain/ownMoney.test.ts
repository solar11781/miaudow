// UI-UX-SPEC section 12d, D-163: revenue = study yield x your price, margin = revenue - your cost, per ha. Yields,
// prices, costs and "Tổng thu" are P-02 Tables 4, 8, 12 and "Lãi thuần" Table 13 (research/price-entry-notes.md
// section 2); the other expected values are worked out by hand (t/ha x đ/kg = thousand đ/ha, rounded once, half up).
import { describe, expect, it } from 'vitest';
import { millionsOf, ownMoney, readMillions, readWhole } from './ownMoney';

const entry = (price: string | null, cost: string | null = null) => ({ price, cost });

describe('your price and costs', () => {
  it('gives the study gross return with the study price, and its net profit with the study cost', () => {
    const p02 = [
      // yield t/ha, price đ/kg, cost and "Tổng thu" thousand đ/ha, "Lãi thuần"
      ['5.01', '7500', '32426', '37,575', '5,149'], // spring rice (usual)
      ['3.91', '28000', '83500', '109,480', '25,980'], // peanut (cc1)
      ['12.2', '11000', '113100', '134,200', '21,100'], // chili (cc2)
      ['50.9', '850', '27400', '43,265', '15,865'], // autumn-winter biomass maize (cc2)
      ['0.72', '50000', '23500', '36,000', '12,500'], // black sesame (cc3)
      ['55.00', '850', '27300', '46,750', '19,450'], // summer-autumn biomass maize (cc4)
      ['12.86', '6500', '63200', '83,590', '20,390'], // sweet potato (cc4)
    ];
    for (const [yieldT = '', price = '', cost = '', gross, profit] of p02) {
      expect(ownMoney([yieldT], [entry(price, cost)]).crops[0]).toEqual({ revenue: gross, margin: profit });
    }
  });

  it('rounds once at the end, half away from zero as the engine does', () => {
    // 1.03 t/ha x 30,050 đ/kg = 30,951.5; minus 31,000 = -48.5
    expect(ownMoney(['1.03'], [entry('30050', '31000')]).crops[0]).toEqual({ revenue: '30,952', margin: '-49' });
  });

  it('shows no margin without a cost and nothing without a price', () => {
    expect(ownMoney(['1.03'], [entry('45000')]).crops[0]).toEqual({ revenue: '46,350', margin: null });
    expect(ownMoney(['1.03'], [entry(null, '25000')]).crops[0]).toEqual({ revenue: null, margin: null });
  });

  it('adds the whole year only when every crop has the numbers, from the unrounded values', () => {
    const yields = ['5.01', '1.03', '10.05']; // usual: rice, black bean, sweet potato
    // 35,070 + 30,951.5 + 55,375.5 = 121,397 (the rounded parts would add to 121,398)
    // margins with the P-02 costs: 2,644 + 5,951.5 + 14,575.5 = 23,171
    const full = ownMoney(yields, [entry('7000', '32426'), entry('30050', '25000'), entry('5510', '40800')]);
    expect(full.crops.map((c) => c.revenue)).toEqual(['35,070', '30,952', '55,376']);
    expect(full.crops.map((c) => c.margin)).toEqual(['2,644', '5,952', '14,576']);
    expect(full.total).toEqual({ revenue: '121,397', margin: '23,171' });

    const noCost = ownMoney(yields, [entry('7000', '32426'), entry('30050'), entry('5510', '40800')]);
    expect(noCost.total).toEqual({ revenue: '121,397', margin: null });
    const noPrice = ownMoney(yields, [entry('7000', '32426'), entry(null, '25000'), entry('5510', '40800')]);
    expect(noPrice.total).toEqual({ revenue: null, margin: null });
  });

  it('stays exact for numbers past the safe integer range', () => {
    // 1.03 x 9,007,199,254,740,993 = 9,277,415,232,383,222.79
    expect(ownMoney(['1.03'], [entry('9007199254740993')]).crops[0]?.revenue).toBe('9,277,415,232,383,223');
  });
});

describe('a typed field', () => {
  it('takes whole numbers of 0 or more, empty as not given, anything else as not used', () => {
    expect(readWhole('')).toBeNull();
    expect(readWhole('0')).toBe('0');
    expect(readWhole('007500')).toBe('7500');
    for (const bad of ['1.5', '-3', '1e3', ' 5', '5,000']) expect(readWhole(bad)).toBe('invalid');
  });
  // privacy review of PR #66: a crafted link with 200,000-digit values froze the cards; 9 digits is a routine cap
  it('takes at most 9 digits and rejects a 200,000-digit value at once', () => {
    expect(readWhole('999999999')).toBe('999999999');
    expect(readWhole('1000000000')).toBe('invalid');
    const start = performance.now();
    expect(readWhole('9'.repeat(200_000))).toBe('invalid');
    expect(performance.now() - start).toBeLessThan(100);
  });
});

// D-192: a cost is typed in million đ/ha like every money number shown (D-190) and kept in thousand đ/ha (D-180)
describe('a cost typed in million đồng per ha', () => {
  it('keeps a typed number of million as whole thousand, with a decimal comma or dot', () => {
    expect(readMillions('')).toBeNull();
    expect(readMillions('24,7')).toBe('24700');
    expect(readMillions('24.7')).toBe('24700');
    expect(readMillions('24,689')).toBe('24689');
    expect(readMillions('83,5')).toBe('83500');
    expect(readMillions('25')).toBe('25000');
    expect(readMillions('0')).toBe('0');
    expect(readMillions('0024,70')).toBe('24700');
  });
  it('rounds to a whole thousand, half up', () => {
    expect(readMillions('24,6894')).toBe('24689');
    expect(readMillions('24,6895')).toBe('24690');
    expect(readMillions('0,0004')).toBe('0');
  });
  it('rejects anything else, and keeps the same 9-digit thousand limit', () => {
    for (const bad of ['-3', '1e3', ' 5', '24,7,1', '1.000,5', ',', 'abc']) expect(readMillions(bad)).toBe('invalid');
    expect(readMillions('999999,999')).toBe('999999999');
    expect(readMillions('999999,9995')).toBe('invalid'); // rounds to 1,000,000,000 thousand, 10 digits
    expect(readMillions('1000000')).toBe('invalid');
    const start = performance.now();
    expect(readMillions('9'.repeat(200_000))).toBe('invalid');
    expect(readMillions(`1,${'9'.repeat(200_000)}`)).toBe('invalid');
    expect(performance.now() - start).toBeLessThan(100);
  });
  it('shows a kept cost back in million, as a number field takes it', () => {
    expect(millionsOf('24700')).toBe('24.7');
    expect(millionsOf('24689')).toBe('24.689');
    expect(millionsOf('25000')).toBe('25');
    expect(millionsOf('5')).toBe('0.005');
    expect(millionsOf('0')).toBe('0');
    expect(millionsOf('999999999')).toBe('999999.999');
    expect(readMillions(millionsOf('24700'))).toBe('24700');
  });
});
