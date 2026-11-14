import { describe, expect, it } from 'vitest';
import { en } from '../../i18n/en';
import { vi } from '../../i18n/vi';
import { readStatusText } from './readStatus';

const V = vi.sheet.readStatusValues;
const E = en.sheet.readStatusValues;

describe('register read status in the source sheet', () => {
  it('translates the status word and the bracket details, keeping ids, dates and names as data', () => {
    expect(readStatusText('READ (full text, VJOL copy 167049)', V)).toBe(
      `${V.READ} (${V.details['full text']}, ${V.vjolCopy('167049')})`,
    );
    expect(readStatusText('READ (full text, VJOL copy 167049)', E)).toBe('Read (full text, VJOL copy 167049)');
    expect(readStatusText('READ (data); licence unclear', V)).toBe(
      `${V.READ} (${V.details.data}); ${V.details['licence unclear']}`,
    );
    expect(readStatusText('READ (ch. 6-8)', V)).toBe(`${V.READ} (${V.chapters('6-8')})`);
    expect(readStatusText('READ (2026-11-13)', V)).toBe(`${V.READ} (2026-11-13)`);
    expect(readStatusText('READ (arXiv)', V)).toBe(`${V.READ} (arXiv)`);
  });
  it('has Vietnamese words for every detail the register uses', () => {
    for (const raw of ['READ (news)', 'READ (file attributes)', 'READ (PDF from team)', 'READ (data)']) {
      expect(readStatusText(raw, V), raw).not.toMatch(/news|file attributes|PDF from team|\(data\)/);
    }
  });
  it('translates every status word of a combined value', () => {
    expect(readStatusText('SUMMARY / READ', V)).toBe(`${V.SUMMARY} / ${V.READ}`);
    expect(readStatusText('NOT READ', E)).toBe(E.NOT_READ);
    expect(readStatusText('ABSTRACT', E)).toBe(E.ABSTRACT);
  });
  it('leaves a value it does not know unchanged', () => {
    expect(readStatusText('partly', V)).toBe('partly');
  });
});
