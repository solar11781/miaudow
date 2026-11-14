// UI-UX-SPEC section 14a test hooks with member B's row names (D-169): card-<plan id> and card-<plan id>-row-<row>.
import { afterEach, describe, expect, it } from 'vitest';
import { cleanup, render } from '@testing-library/react';
import { SettingsProvider } from '../../app/settings';
import { ProvenanceProvider } from '../provenance/ProvenanceProvider';
import { validateCompare } from '../../api';
import { body, compare } from '../../tests/fixtures';
import { PlanCard } from './PlanCard';
import { vi } from '../../i18n/vi';

const ROWS = ['header', 'calendar', 'money', 'weather', 'water', 'land', 'checks', 'why', 'share'];

function renderCard(languages: string[] = ['vi-VN', 'vi']) {
  Object.defineProperty(window.navigator, 'languages', { value: languages, configurable: true });
  const res = validateCompare(compare(), body);
  const plan = res.plans[2];
  if (!plan) throw new Error('no plan');
  plan.money.total = { value: '30,799', unit: { vi: 'nghìn đồng/ha', en: 'thousand đ/ha' }, source_ids: ['R-P02'] };
  const water = { value: '6,500-7,500', unit: { vi: 'm3/ha', en: 'm3/ha' }, source_ids: ['R-P02'] };
  plan.water = [
    { crop_key: plan.calendar[0]?.crop_key ?? '', measure: 'to_apply', value: water, scope: null, note: null },
  ];
  render(
    <SettingsProvider>
      <ProvenanceProvider>
        <PlanCard plan={plan} res={res} priority="water" onShare={async () => true} />
      </ProvenanceProvider>
    </SettingsProvider>,
  );
  return plan.id;
}

describe('plan card test hooks', () => {
  afterEach(cleanup);
  it('marks the card and each of its rows', () => {
    const id = renderCard();
    expect(document.querySelector(`[data-testid="card-${id}"]`)).not.toBeNull();
    for (const row of ROWS) expect(document.querySelector(`[data-testid="card-${id}-row-${row}"]`), row).not.toBeNull();
  });
  it('highlights only the row of the chosen priority', () => {
    const id = renderCard();
    const marked = [...document.querySelectorAll('[data-highlighted="true"]')].map((e) =>
      e.getAttribute('data-testid'),
    );
    expect(marked).toEqual([`card-${id}-row-water`]);
  });
  // review 2026-11-14: Vietnamese digit grouping on every API value, the same string on the card and in the sheet
  it('shows api values in the notation of the language', () => {
    const values = () => [...document.querySelectorAll('[data-value]')].map((e) => e.getAttribute('data-value'));
    renderCard();
    expect(values()).toEqual(expect.arrayContaining(['30.799 nghìn đồng/ha', '6.500-7.500 m³/ha']));
    cleanup();
    renderCard(['en-GB', 'en']);
    expect(values()).toEqual(expect.arrayContaining(['30,799 thousand đ/ha', '6,500-7,500 m³/ha']));
    Object.defineProperty(window.navigator, 'languages', { value: ['vi-VN', 'vi'], configurable: true });
  });
});

// UI-UX-SPEC T16 card-warnings (H17): a screenshot of one card keeps its four warnings
describe('card warnings', () => {
  afterEach(cleanup);
  it('T16 card-warnings: the trial note, the price year, not a forecast and the support note are inside the card', () => {
    const id = renderCard();
    const card = document.querySelector(`[data-testid="card-${id}"]`)?.textContent ?? '';
    for (const line of [vi.farmer.trialNote, vi.common.notForecast, vi.common.support]) expect(card).toContain(line);
    expect(card).toContain(vi.farmer.priceYearNotStated); // the fixture plan states no price year
  });
});

// review 2026-11-14: rule names on the cards are the API's rules[].label, never a second copy in the frontend
describe('rule names', () => {
  afterEach(cleanup);
  it('come from the response', () => {
    const res = validateCompare(compare(), body);
    res.rules = res.rules.map((r) => ({ ...r, label: { vi: `nhãn ${r.code}`, en: `label ${r.code}` } }));
    const plan = res.plans[2];
    if (!plan) throw new Error('no plan');
    render(
      <SettingsProvider>
        <ProvenanceProvider>
          <PlanCard plan={plan} res={res} priority="income" onShare={async () => true} />
        </ProvenanceProvider>
      </SettingsProvider>,
    );
    const heads = [...document.querySelectorAll('thead th')].map((e) => e.textContent);
    for (const code of ['heavy_rain', 'heat', 'cold', 'drought_rain_consecutive', 'drought_rain_any2']) {
      expect(heads).toContain(`nhãn ${code}`);
    }
  });
});

// UI-UX-SPEC section 9: the check row is "always open (no disclosure)"; the why row is a disclosure, collapsed
describe('check and why rows', () => {
  afterEach(cleanup);
  it('keep the risks open and fold only the reasons', () => {
    const id = renderCard();
    expect(document.querySelector(`[data-testid="card-${id}-row-checks"]`)?.closest('details')).toBeNull();
    const why = document.querySelector(`[data-testid="card-${id}-row-why"]`)?.closest('details');
    expect(why).not.toBeNull();
    expect(why?.open).toBe(false);
  });
});

// UI-UX-SPEC section 9: P-02 "lợi nhuận thuần (RVAC) = GR - TVC", labour included; P-03 "Lợi nhuận = GR - Tổng chi phí
// vật chất", material costs only. The API's definition stays; one plain sentence follows it, chosen by the study
// the money cites (D-170), not by the text_only field.
describe('money definition', () => {
  afterEach(cleanup);
  const moneyText = (planIndex: number, study: string) => {
    const res = validateCompare(compare(), body);
    const plan = res.plans[planIndex];
    if (!plan) throw new Error('no plan');
    plan.money.definition = { vi: 'định nghĩa của bài', en: 'the paper definition' };
    plan.calendar = plan.calendar.map((c) => ({ ...c, source_ids: [study] }));
    render(
      <SettingsProvider>
        <ProvenanceProvider>
          <PlanCard plan={plan} res={res} priority="income" onShare={async () => true} />
        </ProvenanceProvider>
      </SettingsProvider>,
    );
    return document.querySelector(`[data-testid="card-${plan.id}-row-money"]`)?.textContent ?? '';
  };
  it('explains the P-02 definition in plain words', () => {
    const text = moneyText(2, 'R-P02');
    expect(text).toContain('định nghĩa của bài');
    expect(text).toContain(vi.farmer.definitionPlain.p02);
  });
  it('explains the P-03 definition in plain words', () => {
    const text = moneyText(1, 'R-P03');
    expect(text).toContain(vi.farmer.definitionPlain.p03);
    expect(text).not.toContain(vi.farmer.definitionPlain.p02);
  });
});

// walkthrough 2026-11-14: the month numbers under the calendar bar say what they are
describe('calendar axis', () => {
  afterEach(cleanup);
  it('is labelled with the word month', () => {
    const id = renderCard();
    expect(document.querySelector(`[data-testid="card-${id}-row-calendar"]`)?.textContent).toContain(
      vi.farmer.monthAxis,
    );
  });
});

// walkthrough 2026-11-14 and D-68: a note shared by several TCVN rows of one crop is said once, above those rows
describe('water notes', () => {
  afterEach(cleanup);
  it('say a shared note once per crop', () => {
    const res = validateCompare(compare(), body);
    const plan = res.plans[2];
    const key = plan?.calendar[0]?.crop_key;
    if (!plan || !key) throw new Error('no plan');
    const note = { vi: 'Tiêu chuẩn không nói Nghệ An thuộc vùng nào.', en: 'The standard does not place Nghệ An.' };
    const value = { value: '6,500-7,500', unit: { vi: 'm3/ha', en: 'm3/ha' }, source_ids: ['R-P02'] };
    plan.water = ['Trung bộ, cấy', 'Trung bộ, gieo thẳng', 'Bắc bộ'].map((region) => ({
      crop_key: key,
      measure: 'to_apply' as const,
      value,
      scope: { vi: region, en: region },
      note,
    }));
    render(
      <SettingsProvider>
        <ProvenanceProvider>
          <PlanCard plan={plan} res={res} priority="income" onShare={async () => true} />
        </ProvenanceProvider>
      </SettingsProvider>,
    );
    const water = document.querySelector(`[data-testid="card-${plan.id}-row-water"]`)?.textContent ?? '';
    expect(water.split(note.vi)).toHaveLength(2);
    expect(water.indexOf(note.vi)).toBeLessThan(water.indexOf('Trung bộ, cấy'));
  });
});

// D-170: the per-year share tables of the stability and water rows fold behind "Xem từng năm"; the rows stay open
describe('per-year tables', () => {
  afterEach(cleanup);
  it('fold behind an accessible button and stay in the page for print', async () => {
    const id = renderCard();
    for (const row of ['weather', 'water']) {
      const box = document.querySelector(`[data-testid="card-${id}-row-${row}"]`);
      const button = [...(box?.querySelectorAll('button') ?? [])].find((b) => b.textContent === vi.farmer.eachYear);
      expect(button?.getAttribute('aria-expanded'), row).toBe('false');
      const panel = document.getElementById(button?.getAttribute('aria-controls') ?? '');
      expect(panel?.querySelector('table'), row).not.toBeNull();
      expect(panel?.hasAttribute('hidden'), row).toBe(false); // hidden by screen-only CSS, so print shows it (T35)
      button?.click();
      await Promise.resolve();
      expect(button?.getAttribute('aria-expanded'), row).toBe('true');
    }
  });
});
