import { afterEach, describe, expect, it } from 'vitest';
import { cleanup, fireEvent, render } from '@testing-library/react';
import { SettingsProvider } from '../app/settings';
import { ProvenanceProvider } from '../features/provenance/ProvenanceProvider';
import { PlanCard } from '../features/farmer/PlanCard';
import { validateCompare } from '../api';
import { body, compare, moneyItem } from '../tests/fixtures';
import { NO_OWN } from '../domain/farmerState';
import { answer, type Fmt } from '../features/ai/answer';
import { PASSAGES } from '../features/ai/knowledge';
import { en } from './en';
import { vi } from './vi';

// F9, D-190: money a farmer sees is in million dong per hectare (vi "triệu đồng/ha", en "million VND/ha"); the
// paper's thousand dong per hectare (P-02 Table 13) stays in the source sheet; English writes VND, never đ; and a
// plan is named by planLabel, never by the paper's bare code (CC1...).
const MILLION = { vi: 'triệu đồng/ha', en: 'million VND/ha' } as const;
const THOUSAND = { vi: /nghìn đ/, en: /thousand/ } as const;
const DONG_IN_EN = /(^|[\s(\d])đ(?=\/|\s|$|\))/;
const BARE_CODE = /\bCC\d\b/i;

const own = { values: NO_OWN, set: () => undefined };
const f: Fmt = { pct: (v) => `${v}`, signedPct: (v) => `${v}`, n: (v, d = 0) => v.toFixed(d) };
const text = { noEvidence: 'NO_EVIDENCE', noRanking: 'NO_RANKING' };

function renderCard(lang: 'vi' | 'en') {
  const languages = lang === 'vi' ? ['vi-VN', 'vi'] : ['en-GB', 'en'];
  Object.defineProperty(window.navigator, 'languages', { value: languages, configurable: true });
  const res = validateCompare(compare(), body);
  const plan = res.plans.find((p) => p.id === 'cc1');
  if (!plan) throw new Error('no cc1');
  // the API's units (rules/rotations.yaml reported_economics.unit and price_unit)
  const unit = { vi: 'nghìn đồng/ha', en: 'thousand VND/ha' };
  const item = moneyItem('cc1_spring_peanut', '3.91', '31,357', '25,980', '24,689');
  item.profit.unit = unit;
  if (item.cost) item.cost.unit = unit;
  item.price.unit = { vi: 'đồng/kg', en: 'VND/kg' };
  plan.money.items = [item];
  plan.money.total = { value: '53,380', unit, source_ids: ['R-P02'] };
  render(
    <SettingsProvider>
      <ProvenanceProvider>
        <PlanCard plan={plan} res={res} priority="income" own={own} onShare={async () => true} />
      </ProvenanceProvider>
    </SettingsProvider>,
  );
  return plan;
}

/** What a sighted reader sees in an element: no screen-reader text and no form labels (the cost is typed in the
 * paper's unit). */
function seen(selector: string) {
  const el = document.querySelector(selector)?.cloneNode(true);
  if (!(el instanceof HTMLElement)) throw new Error(`no ${selector}`);
  for (const hidden of el.querySelectorAll('.visually-hidden, label')) hidden.remove();
  return el.textContent ?? '';
}

describe('one money unit (F9, D-190)', () => {
  afterEach(() => {
    cleanup();
    Object.defineProperty(window.navigator, 'languages', { value: ['vi-VN', 'vi'], configurable: true });
  });

  it('the unit texts are million dong per hectare, and English writes VND', () => {
    expect(vi.common.millionPerHa).toBe(MILLION.vi);
    expect(en.common.millionPerHa).toBe(MILLION.en);
    expect(vi.common.perKg).toBe('đồng/kg');
    expect(en.common.perKg).toBe('VND/kg');
  });

  it.each(['vi', 'en'] as const)('the plan card shows money in million per hectare (%s)', (lang) => {
    renderCard(lang);
    for (const where of ['[data-testid="card-cc1-row-money"]', '[data-testid="card-cc1-row-header"]']) {
      const shown = seen(where);
      expect(shown, where).toContain(MILLION[lang]);
      expect(shown, where).not.toMatch(THOUSAND[lang]);
      if (lang === 'en') expect(shown, where).not.toMatch(DONG_IN_EN);
    }
    // 53,380 and 25,980 thousand VND/ha (P-02 Table 13) shown as 53.4 and 26.0 million
    const money = seen('[data-testid="card-cc1-row-money"]');
    expect(money).toContain(lang === 'vi' ? '53,4' : '53.4');
    expect(money).toContain(lang === 'vi' ? '26,0' : '26.0');
  });

  it('the source sheet keeps the paper value and unit exactly', () => {
    renderCard('vi');
    const button = document.querySelector('[data-testid="card-cc1-row-money"] ul button[data-value]');
    if (!(button instanceof HTMLElement)) throw new Error('no profit button');
    expect(button.getAttribute('data-value')).toBe('25.980 nghìn đồng/ha');
    fireEvent.click(button);
    expect(document.querySelector('[data-testid="source-sheet"] h2')?.textContent).toBe('25.980 nghìn đồng/ha');
  });

  it('the plan card names the plan by its label, with the crops under it', () => {
    renderCard('vi');
    const head = seen('[data-testid="card-cc1-row-header"]');
    expect(head).toContain(vi.farmer.trialShort('1'));
    expect(head).not.toMatch(BARE_CODE);
  });

  it.each([
    ['vi', 'trong lac lai bao nhieu'],
    ['vi', 'Nên trồng gì cho ruộng nhà tôi?'],
    ['en', 'trong lac lai bao nhieu'],
    ['en', 'Nên trồng gì cho ruộng nhà tôi?'],
  ] as const)('the assistant shows money in million and plans by name (%s: %s)', (lang, q) => {
    const a = answer(q, lang, f, text);
    const money = a.lines.flatMap((l) => (l.ref && l.ref.sourceId === 'p02' ? [l.ref.value] : []));
    expect(money.length).toBeGreaterThan(0);
    for (const m of money) expect(m).toContain(MILLION[lang]);
    for (const l of a.lines) {
      expect(l.text).not.toMatch(BARE_CODE);
      if (lang === 'en') expect(`${l.text} ${l.ref?.value ?? ''} ${l.ref?.detail ?? ''}`).not.toMatch(DONG_IN_EN);
    }
  });

  it('the assistant passages name the plans by their label', () => {
    for (const p of PASSAGES) for (const title of Object.values(p.title)) expect(title).not.toMatch(BARE_CODE);
  });

  it('the English text file never writes đ as a unit', () => {
    const walk = (v: unknown): string[] =>
      typeof v === 'string'
        ? [v]
        : typeof v === 'function'
          ? walk(Reflect.apply(v, undefined, ['1', '2', '3']))
          : v && typeof v === 'object'
            ? Object.values(v).flatMap(walk)
            : [];
    for (const s of walk(en)) expect(s).not.toMatch(DONG_IN_EN);
  });
});
