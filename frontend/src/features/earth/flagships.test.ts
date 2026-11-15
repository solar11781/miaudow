// H15: the satellite labels come from the vi and en text files.
import { describe, expect, it } from 'vitest';
import { en } from '../../i18n/en';
import { vi } from '../../i18n/vi';
import { FLAGSHIPS } from './flagships';

describe('flagship satellites', () => {
  it('take their labels from the text files', () => {
    expect(FLAGSHIPS.map((f) => f.label)).toEqual([
      { vi: vi.earth.flagships.vn, en: en.earth.flagships.vn },
      { vi: vi.earth.flagships.terra, en: en.earth.flagships.terra },
    ]);
  });
});
