// D-174: a shared card opens under the path of the language it was shared in; the answers stay as they are.
import { describe, expect, it } from 'vitest';
import { cardUrl } from './PlansStep';

describe('card share link', () => {
  const answers = new URLSearchParams('ruong=canal_end&nam=2010,2020&uutien=income&the=cc3');
  const base = `${window.location.origin}${window.location.pathname}`;
  it('uses the Vietnamese path in Vietnamese', () => {
    expect(cardUrl(answers, 'vi')).toBe(`${base}#/nong-dan/phuong-an?${answers.toString()}`);
  });
  it('uses the English path in English', () => {
    expect(cardUrl(answers, 'en')).toBe(`${base}#/farmer/plans?${answers.toString()}`);
  });
});
