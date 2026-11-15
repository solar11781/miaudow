import { describe, expect, it } from 'vitest';
import { browserLang } from '../app/settings';
import { PLANS } from '../domain/plans';
import { decisionPlan, MISSING_INFORMATION, officerQuestions, RULEBOOK_ID, rulebookPlan } from './rulebook';

describe('governed plan text', () => {
  it('every plan has its rulebook entry and decision text', () => {
    for (const p of PLANS) {
      expect(rulebookPlan(p.id), p.id).toBeDefined();
      expect(decisionPlan(p.id)?.applicability.unknown, p.id).toBeDefined();
    }
  });
  it('every risk line names its source and where in it', () => {
    for (const p of PLANS) {
      for (const r of rulebookPlan(p.id)?.risk_lines ?? []) {
        expect(r.source_id).toMatch(/^R-/);
        expect(r.location.length).toBeGreaterThan(0);
        expect(r.quote.length).toBeGreaterThan(0);
      }
    }
  });
  it('the decision text never ranks and always lists what the app cannot know', () => {
    expect(MISSING_INFORMATION.length).toBeGreaterThan(2);
    const all = JSON.stringify(PLANS.map((p) => decisionPlan(p.id))).toLowerCase();
    for (const w of ['tốt nhất', 'nên chọn', 'the best', 'we recommend']) expect(all).not.toContain(w);
  });
});

describe('starting language (H16)', () => {
  it('is Vietnamese when the browser lists Vietnamese, English otherwise', () => {
    expect(browserLang(['en-US', 'vi-VN'])).toBe('vi');
    expect(browserLang(['vi'])).toBe('vi');
    expect(browserLang(['en-GB', 'fr'])).toBe('en');
    expect(browserLang(undefined)).toBe('en');
  });
});

// D-187 (F5): the farmer's cards read the officer questions by the API's plan id
describe('questions for the officer by API plan id', () => {
  it('are the decision text of the same plan', () => {
    for (const p of PLANS)
      expect(officerQuestions(RULEBOOK_ID[p.id]), p.id).toEqual(decisionPlan(p.id)?.questions_for_officer);
  });
});
