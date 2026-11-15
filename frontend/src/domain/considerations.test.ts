// D-187 (roleplay audit 2026-11-15, F4): each risk quote of a plan card gets one plain line, saying no more than the
// quote. The quotes are the rulebook's risk lines (rules/rotations.yaml, the text the API sends as why.risks).
import { describe, expect, it } from 'vitest';
import { rulebookPlan } from '../data/rulebook';
import { PLANS } from './plans';
import { consideration } from './considerations';
import { vi } from '../i18n/vi';
import { en } from '../i18n/en';
import type { RiskItem } from '../types';
import decision from '../../data/canonical/decision.json';

const QUOTES: RiskItem[] = [
  ...new Map(
    PLANS.flatMap((p) => rulebookPlan(p.id)?.risk_lines ?? []).map((r) => [
      r.text.vi,
      { text: r.text, source_ids: [r.source_id] },
    ]),
  ).values(),
];
const numbers = (text: string) => text.match(/\d+/g) ?? [];

describe('plain lines of the risk quotes', () => {
  it('cover each distinct quote of the six plans with a line of its own', () => {
    const keys = QUOTES.map(consideration);
    expect(QUOTES).toHaveLength(6);
    expect(keys).not.toContain(null);
    expect(new Set(keys).size).toBe(QUOTES.length);
  });
  it('carry no number that their quote does not, in both languages', () => {
    for (const quote of QUOTES) {
      const key = consideration(quote);
      if (!key) throw new Error(quote.text.vi);
      for (const [dict, lang] of [
        [vi, 'vi'],
        [en, 'en'],
      ] as const) {
        const line = dict.farmer.considerations[key];
        for (const n of numbers(line.line)) expect(numbers(quote.text[lang]), `${key} ${lang} ${n}`).toContain(n);
        expect(line.source.length, key).toBeGreaterThan(0);
      }
    }
  });
  it('keep the 2-3 times of the cost quote as written', () => {
    expect(vi.farmer.considerations.cost.line).toContain('2-3 lần');
    expect(en.farmer.considerations.cost.line).toContain('2-3 times');
  });
  it('give a quote with no line no key, so the card shows it in full', () => {
    expect(consideration({ text: { vi: 'Một câu khác', en: 'Another quote' }, source_ids: ['R-P02'] })).toBeNull();
    // the cost quote of P-02 under another source's id
    const cost = QUOTES.find((q) => q.source_ids.includes('R-P02'));
    if (!cost) throw new Error('no quote');
    expect(consideration({ ...cost, source_ids: ['R-P03'] })).toBeNull();
  });
});

// the paper says "thường cao gấp 2 - 3 lần" (usually, tr. 48); the officer questions now on every card must not
// soften it to "có thể" (may) (rules/rotations.yaml, R-P02)
describe('the officer questions word the cost as the paper does', () => {
  it('says usually, not may', () => {
    const text = JSON.stringify(decision);
    expect(text).not.toMatch(/có thể gấp 2-3 lần|can cost 2-3 times/);
    expect(text).toMatch(/thường gấp 2-3 lần/);
    expect(text).toMatch(/usually cost 2-3 times/);
  });
});
