import { describe, expect, it } from 'vitest';
import { hazards, type Magnitude } from '../data';
import { magnitudeDigits } from './hazards';

// visual audit 2026-11-16: the data room wrote a count of months as "7,0". Days and months are counts in the data
// file (whole numbers only); the largest daily rain is measured in tenths of a millimetre.
describe('digits of a measured value', () => {
  it('writes no decimal for a quantity the data holds as whole numbers, and one for the others', () => {
    for (const [key, cells] of Object.entries(hazards.magnitudes)) {
      const whole = Object.values(cells)
        .flat()
        .every((v) => Number.isInteger(v));
      expect(magnitudeDigits(key as Magnitude), key).toBe(whole ? 0 : 1);
    }
  });
});
