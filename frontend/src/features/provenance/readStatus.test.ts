import { describe, expect, it } from 'vitest';
import { en } from '../../i18n/en';
import { vi } from '../../i18n/vi';
import { readStatusText } from './readStatus';

describe('register read status in the source sheet', () => {
  it('translates the status word and keeps the copy detail as data', () => {
    expect(readStatusText('READ (full text, VJOL copy 167049)', vi.sheet.readStatusValues)).toBe(
      `${vi.sheet.readStatusValues.READ} (full text, VJOL copy 167049)`,
    );
    expect(readStatusText('READ', en.sheet.readStatusValues)).toBe(en.sheet.readStatusValues.READ);
  });
  it('translates every status word of a combined value', () => {
    expect(readStatusText('SUMMARY / READ', vi.sheet.readStatusValues)).toBe(
      `${vi.sheet.readStatusValues.SUMMARY} / ${vi.sheet.readStatusValues.READ}`,
    );
    expect(readStatusText('NOT READ', en.sheet.readStatusValues)).toBe(en.sheet.readStatusValues.NOT_READ);
    expect(readStatusText('ABSTRACT', en.sheet.readStatusValues)).toBe(en.sheet.readStatusValues.ABSTRACT);
  });
  it('leaves a value it does not know unchanged', () => {
    expect(readStatusText('partly', vi.sheet.readStatusValues)).toBe('partly');
  });
});
