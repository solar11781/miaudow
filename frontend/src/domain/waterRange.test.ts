// D-175: the card head shows, per crop, the lowest to the highest of the TCVN 8641 "water to apply" rows the API sends.
// Rows from /api/compare (2026-11-15): spring rice has three TCVN rows and one FAO row; cc1 peanut one TCVN row.
import { describe, expect, it } from 'vitest';
import type { WaterFact } from '../types';
import { parseRange, tcvnRange } from './waterRange';

const m3 = { vi: 'm3/ha', en: 'm3/ha' };
const fact = (measure: WaterFact['measure'], value: string | null, ids = ['R-W15'], unit = m3): WaterFact => ({
  crop_key: 'k',
  measure,
  value: value === null ? null : { value, unit, source_ids: ids },
  scope: null,
  note: null,
});

describe('parseRange', () => {
  it('reads one value or a low-high range in the API notation', () => {
    expect(parseRange('2,000')).toEqual([2000, 2000]);
    expect(parseRange('6,500-7,500')).toEqual([6500, 7500]);
    expect(parseRange('1,200-1,400')).toEqual([1200, 1400]);
    expect(parseRange('450.5-700')).toEqual([450.5, 700]);
  });
  it('refuses anything else', () => {
    for (const s of ['', 'about 2,000', '6,500 - 7,500', '7,500-6,500', '2,00', '-2,000', '1,2,3'])
      expect(parseRange(s), s).toBeNull();
  });
});

describe('tcvnRange', () => {
  it('spans the lowest to the highest TCVN row and leaves the FAO row out (spring rice)', () => {
    const rice = [
      fact('to_apply', '6,500-7,500'),
      fact('to_apply', '6,500-7,500'),
      fact('to_apply', '6,000-7,000'),
      fact('crop_uses', '450-700', ['R-M02'], { vi: 'mm', en: 'mm' }),
    ];
    expect(tcvnRange(rice)).toEqual({ value: '6,000-7,500', unit: m3, source_ids: ['R-W15'] });
  });
  it('shows the single value of a crop with one row (cc1 peanut)', () => {
    expect(tcvnRange([fact('to_apply', '2,000'), fact('crop_uses', '500-700', ['R-M02'])])).toEqual({
      value: '2,000',
      unit: m3,
      source_ids: ['R-W15'],
    });
  });
  it('shows one value when every row gives the same one', () => {
    expect(tcvnRange([fact('to_apply', '2,000'), fact('to_apply', '2,000')])?.value).toBe('2,000');
  });
  it('keeps the source ids of every row it spans', () => {
    expect(tcvnRange([fact('to_apply', '2,000', ['R-W15']), fact('to_apply', '2,500', ['R-W16'])])).toMatchObject({
      value: '2,000-2,500',
      source_ids: ['R-W15', 'R-W16'],
    });
  });
  it('gives no figure without a TCVN row, with a row it cannot read, or with rows in other units', () => {
    expect(tcvnRange([fact('not_listed', null)])).toBeNull();
    expect(tcvnRange([fact('crop_uses', '500-700', ['R-M02'])])).toBeNull();
    expect(tcvnRange([fact('to_apply', '2,000'), fact('to_apply', 'about 3,000')])).toBeNull();
    expect(
      tcvnRange([fact('to_apply', '2,000'), fact('to_apply', '200', ['R-W15'], { vi: 'mm', en: 'mm' })]),
    ).toBeNull();
  });
});
