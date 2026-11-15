// UI-UX-SPEC section 14a test hooks with member B's row names (D-169): card-<plan id> and card-<plan id>-row-<row>.
import { afterEach, describe, expect, it, onTestFinished, vi as mock } from 'vitest';
import { cleanup, fireEvent, render, within } from '@testing-library/react';
import { SettingsProvider, useSettings } from '../../app/settings';
import { ProvenanceProvider } from '../provenance/ProvenanceProvider';
import { validateCompare } from '../../api';
import { body, compare, moneyItem } from '../../tests/fixtures';
import { PlanCard } from './PlanCard';
import { NO_OWN } from '../../domain/farmerState';
import { vi } from '../../i18n/vi';
import { en } from '../../i18n/en';
import { SOURCES } from '../../domain/sources';
import { decisionPlan, rulebookPlan } from '../../data/rulebook';
import type { Plan, SeasonValue } from '../../types';

const own = { values: NO_OWN, set: () => undefined };
const ROWS = ['header', 'calendar', 'money', 'weather', 'water', 'land', 'checks', 'why', 'share'];

function renderCard(languages: string[] = ['vi-VN', 'vi'], edit?: (plan: Plan) => void) {
  Object.defineProperty(window.navigator, 'languages', { value: languages, configurable: true });
  const res = validateCompare(compare(), body);
  const plan = res.plans[2];
  if (!plan) throw new Error('no plan');
  plan.money.total = { value: '30,799', unit: { vi: 'nghìn đồng/ha', en: 'thousand VND/ha' }, source_ids: ['R-P02'] };
  const water = { value: '6,500-7,500', unit: { vi: 'm3/ha', en: 'm3/ha' }, source_ids: ['R-P02'] };
  plan.water = [
    { crop_key: plan.calendar[0]?.crop_key ?? '', measure: 'to_apply', value: water, scope: null, note: null },
  ];
  edit?.(plan);
  render(
    <SettingsProvider>
      <ProvenanceProvider>
        <PlanCard plan={plan} res={res} priority="water" own={own} onShare={async () => true} />
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
    expect(values()).toEqual(expect.arrayContaining(['30,799 thousand VND/ha', '6,500-7,500 m³/ha']));
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
  // D-187: these stay on the card when the source notes move to the sheets (UI-UX-SPEC 12b, section 9 water row)
  it('keep the statistics office credit in the rice block and the model label of soil wetness', () => {
    const id = renderCard();
    const rice = document.querySelector(`[data-testid="card-${id}-row-weather"]`)?.textContent ?? '';
    expect(rice).toContain(vi.farmer.rice.nsoCredit);
    const water = document.querySelector(`[data-testid="card-${id}-row-water"]`)?.textContent ?? '';
    expect(water).toContain(vi.farmer.rows.soilNote);
    expect(vi.farmer.rows.soilNote).toContain('Giá trị mô hình NASA');
    expect(vi.farmer.rows.soilNote).toContain('không phải số đo tại ruộng');
    expect(en.farmer.rows.soilNote).toContain('not a field measurement');
  });
  it('open the long soil note with each soil wetness value', () => {
    const id = renderCard();
    const water = document.querySelector(`[data-testid="card-${id}-row-water"]`);
    expect(water?.textContent).not.toContain('MERRA-2');
    const soil = [...(water?.querySelectorAll('p') ?? [])].find((p) => p.textContent === vi.farmer.rows.soil);
    const button = soil?.parentElement?.querySelector('button[data-value]');
    if (!(button instanceof HTMLElement)) throw new Error('no soil value');
    fireEvent.click(button);
    expect(document.querySelector('[data-testid="source-sheet"]')?.textContent).toContain(vi.farmer.rows.soilSheetNote);
    expect(vi.farmer.rows.soilSheetNote).toContain('MERRA-2');
  });
});

// D-64, D-68 and UI-UX-SPEC section 9 water row: the card shows TCVN 8641 (m³/ha) and FAO (mm) values as separate
// facts; the spec lists no unit conversion, and one next to the FAO values invites the comparison
describe('water units', () => {
  afterEach(cleanup);
  it('carry no conversion between the two sources, on the card or in the TCVN source sheet', () => {
    const id = renderCard();
    const card = document.querySelector(`[data-testid="card-${id}"]`)?.textContent ?? '';
    // D-187: the TCVN note opens with the TCVN values instead of closing the row
    expect(card).not.toContain(vi.farmer.rows.waterNote);
    const row = document.querySelector(`[data-testid="card-${id}-row-water"]`) ?? document;
    expect(sheetOf('6.500-7.500 m³/ha', row)).toContain(vi.farmer.rows.waterNote);
    for (const text of [card, vi.farmer.rows.waterNote, en.farmer.rows.waterNote])
      expect(text).not.toMatch(/0[,.]1 mm/);
    for (const text of Object.values(SOURCES.tcvn8641.caveat)) expect(text).not.toMatch(/0[,.]1 mm/);
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
          <PlanCard plan={plan} res={res} priority="income" own={own} onShare={async () => true} />
        </ProvenanceProvider>
      </SettingsProvider>,
    );
    const heads = [...document.querySelectorAll('thead th')].map((e) => e.textContent);
    for (const code of ['heavy_rain', 'heat', 'cold', 'drought_rain_consecutive', 'drought_rain_any2']) {
      expect(heads).toContain(`nhãn ${code}`);
    }
  });
});

// D-187 item 4 (F1, replaces section 9's "every row stays open"): the card face fits one phone screen, so each row
// under the head folds behind its own heading button; the folded part stays in the page, so print shows it (T35)
const FOLDED = ['calendar', 'money', 'weather', 'water', 'land', 'checks', 'why'];
describe('card face', () => {
  afterEach(cleanup);
  it('folds each row behind one heading button, closed at first', async () => {
    const id = renderCard();
    for (const row of FOLDED) {
      const box = document.querySelector(`[data-testid="card-${id}-row-${row}"]`);
      const button = box?.querySelector('h3 > button');
      expect(button?.getAttribute('aria-expanded'), row).toBe('false');
      const panel = document.getElementById(button?.getAttribute('aria-controls') ?? '');
      expect(box?.contains(panel ?? null), row).toBe(true);
      expect(panel?.hasAttribute('hidden'), row).toBe(false);
      (button as HTMLButtonElement | null)?.click();
      await Promise.resolve();
      expect(button?.getAttribute('aria-expanded'), row).toBe('true');
    }
  });
  it('keeps the warnings and the priority label outside every fold (H17, H11)', () => {
    const id = renderCard();
    const panels = [...document.querySelectorAll('h3 > button')].map((b) =>
      document.getElementById(b.getAttribute('aria-controls') ?? ''),
    );
    const folded = (el: Element) => panels.some((p) => p?.contains(el));
    const card = document.querySelector(`[data-testid="card-${id}"]`);
    for (const line of [vi.farmer.trialNote, vi.farmer.priceYearNotStated, vi.common.notForecast, vi.common.support]) {
      const el = [...(card?.querySelectorAll('p') ?? [])].find((p) => p.textContent === line);
      expect(el && !folded(el), line).toBe(true);
    }
    const water = document.querySelector(`[data-testid="card-${id}-row-water"] h3 > button`);
    expect(water?.textContent).toContain(vi.farmer.yourPriority);
  });
  // tonight's walkthrough of F1: the folded things-to-weigh row says on its face how many it holds
  it('shows the number of things to weigh in its heading, only when there are some', () => {
    const heading = (id: string) => document.querySelector(`[data-testid="card-${id}-row-checks"] h3 > button`);
    const id = renderCard(['vi-VN', 'vi'], (plan) => {
      plan.why.risks = [1, 2, 3].map((n) => ({ text: { vi: `rủi ro ${n}`, en: `risk ${n}` }, source_ids: [] }));
    });
    expect(heading(id)?.textContent).toContain('Cần cân nhắc (3)');
    cleanup();
    const two = renderCard(['en-GB', 'en'], (plan) => {
      plan.why.risks = plan.why.risks.concat(plan.why.risks.map((r) => ({ ...r, text: { vi: 'khác', en: 'other' } })));
    });
    expect(heading(two)?.textContent).toContain('Weigh this (2)');
    cleanup();
    const none = renderCard(['en-GB', 'en'], (plan) => {
      plan.why.risks = [];
    });
    expect(heading(none)?.textContent).toContain(en.farmer.rows.checks);
    expect(heading(none)?.textContent).not.toContain('(');
    Object.defineProperty(window.navigator, 'languages', { value: ['vi-VN', 'vi'], configurable: true });
  });
});

/** Taps the source button showing `value` and returns the text of the sheet it opens. */
// D-191: the P-03 rice control per season as rules/rotations.yaml holds it (P-03 pp. [2], [4]-[5]), never summed
const P03_UNIT = { vi: 'triệu đồng/ha', en: 'million VND/ha' };
const P03_SEASONS: SeasonValue[] = [
  {
    season: 'spring',
    value: { value: '5.36', unit: P03_UNIT, source_ids: ['R-P03'] },
    page: '4-5',
    words: { vi: 'Lúa vụ Đông Xuân 2021 (đối chứng): hiệu quả kinh tế 5,36 triệu đồng/ha.', en: 'x' },
  },
  {
    season: 'summer_autumn',
    value: { value: '1.16', unit: P03_UNIT, source_ids: ['R-P03'] },
    page: '4',
    words: { vi: 'Lúa vụ Hè Thu 2020 (đối chứng): "gần như không có lợi nhuận".', en: 'x' },
  },
  { season: 'autumn_winter', value: null, page: '2', words: { vi: 'Vụ Thu Đông: bỏ hoang.', en: 'x' } },
];

function sheetOf(value: string, root: ParentNode = document): string {
  const button = [...root.querySelectorAll('button[data-value]')].find((e) => e.getAttribute('data-value') === value);
  if (!(button instanceof HTMLElement)) throw new Error(`no button ${value}`);
  fireEvent.click(button);
  return document.querySelector('[data-testid="source-sheet"]')?.textContent ?? '';
}

// D-187 (roleplay audit 2026-11-15, F2): the money row keeps one short label per number; the paper's definition
// (UI-UX-SPEC section 9: P-02 "lợi nhuận thuần (RVAC) = GR - TVC", labour included; P-03 "Lợi nhuận = GR - Tổng chi phí
// vật chất", material costs only), its plain sentence chosen by the study the money cites (D-170), the table number,
// the "our addition" wording and the paper's Table 4 remark open with the number they belong to. Values from
// rules/rotations.yaml (cc1).
describe('money notes', () => {
  afterEach(cleanup);
  const P02_DEF = {
    vi: 'lợi nhuận thuần (RVAC) = GR - TVC; TVC gồm vật tư, công lao động, năng lượng và lãi vay',
    en: 'net profit (RVAC) = GR - TVC (gross return minus total variable cost); TVC counts materials, labour, energy and interest',
  };
  const P03_DEF = { vi: 'Lợi nhuận = GR - Tổng chi phí vật chất', en: 'Profit = GR - total material costs' };
  const FLAG = {
    vi: 'Trong Bảng 4 của bài báo, dòng đậu xanh (CC1) và dòng đậu đen (CC5) giống hệt nhau ở mọi cột; bài báo không giải thích điều này.',
    en: 'In Table 4 of the paper, the CC1 mung bean row and the CC5 black bean row are the same in every column; the paper does not explain this.',
  };
  const money = (planIndex: number, study: 'R-P02' | 'R-P03') => {
    const res = validateCompare(compare(), body);
    const plan = res.plans[planIndex];
    if (!plan) throw new Error('no plan');
    plan.calendar = plan.calendar.map((c) => ({ ...c, source_ids: [study] }));
    if (study === 'R-P02') {
      plan.money.definition = P02_DEF;
      plan.money.items = [
        { ...moneyItem('cc1_summer_autumn_mung_bean', '1.03', '40,000', '16,200', '25,000'), flag: FLAG },
      ];
      plan.money.total = {
        value: '53,380',
        unit: { vi: 'nghìn đồng/ha', en: 'thousand VND/ha' },
        source_ids: ['R-P02'],
      };
    } else {
      plan.money = { ...plan.money, definition: P03_DEF, items: [], total: null, season_values: P03_SEASONS };
      res.sources = { ...res.sources, 'R-P03': { ...res.sources['R-P02'], id: 'R-P03' } } as typeof res.sources;
    }
    render(
      <SettingsProvider>
        <ProvenanceProvider>
          {/* not the income priority: its priority line labels the totals for screen readers in its own words */}
          <PlanCard plan={plan} res={res} priority="water" own={own} onShare={async () => true} />
        </ProvenanceProvider>
      </SettingsProvider>,
    );
    return document.querySelector(`[data-testid="card-${plan.id}-row-money"]`)?.textContent ?? '';
  };
  it('labels each P-02 number in a few words and keeps the notes off the card', () => {
    const text = money(2, 'R-P02');
    for (const label of [vi.farmer.rows.money, vi.farmer.profit, vi.farmer.cost, vi.farmer.own.yearSum])
      expect(text).toContain(label);
    for (const note of ['Bảng', 'RVAC', vi.farmer.ourSum, vi.farmer.definitionPlain.p02])
      expect(text).not.toContain(note);
  });
  it('opens the definition, the table and the Table 4 remark with the profit of the crop', () => {
    money(2, 'R-P02');
    const sheet = sheetOf('16.200 nghìn đồng/ha');
    for (const note of [vi.farmer.profitTable, P02_DEF.vi, vi.farmer.definitionPlain.p02, FLAG.vi])
      expect(sheet).toContain(note);
  });
  it('opens the Table 4 remark with the cost of the crop', () => {
    money(2, 'R-P02');
    expect(sheetOf('25.000 nghìn đồng/ha')).toContain(FLAG.vi);
  });
  it('opens the "our addition" wording and the definition with the whole-year total', () => {
    money(2, 'R-P02');
    const sheet = sheetOf('53.380 nghìn đồng/ha');
    for (const note of [vi.farmer.ourSumNote, P02_DEF.vi]) expect(sheet).toContain(note);
  });
  // never compare P-03 money with P-02 money (UI-UX-SPEC section 9): the P-03 card keeps saying, in one plain line,
  // that its profit takes off material costs only
  // D-192: the plain "in other words" line comes right under the number, before the source block
  it('puts the plain line under the number of the whole-year total and the crop profit, before the source', () => {
    money(2, 'R-P02');
    for (const value of ['53.380 nghìn đồng/ha', '16.200 nghìn đồng/ha']) {
      const sheet = sheetOf(value);
      const plain = sheet.indexOf(vi.farmer.definitionPlain.p02);
      expect(plain, value).toBeGreaterThan(sheet.indexOf(value));
      expect(plain, value).toBeLessThan(sheet.indexOf(vi.sheet.placeYears));
      expect(sheet.split(vi.farmer.definitionPlain.p02), value).toHaveLength(2);
    }
  });
  it('keeps the plain P-03 definition on the card and its paper definition in the sheet', () => {
    const text = money(1, 'R-P03');
    expect(text).toContain(vi.farmer.definitionPlain.p03);
    expect(text).not.toContain(P03_DEF.vi);
    expect(sheetOf('5,36 triệu đồng/ha')).toContain(P03_DEF.vi);
  });
  it('shows each P-03 season as the paper gives it, in its million unit, with no whole-year total', () => {
    const text = money(1, 'R-P03');
    for (const shown of ['5,36', '1,16', 'triệu đồng/ha', 'Vụ Thu Đông: bỏ hoang.']) expect(text).toContain(shown);
    expect(text).not.toContain(vi.farmer.own.yearSum);
    expect(text).not.toContain('6,52'); // never the sum of the two seasons
    expect(sheetOf('1,16 triệu đồng/ha')).toContain(vi.farmer.paperPage('4'));
    expect(sheetOf('5,36 triệu đồng/ha')).toContain(P03_SEASONS[0]?.words.vi);
    expect(sheetOf('Vụ Thu Đông: bỏ hoang.')).toContain(vi.farmer.paperPage('2'));
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

// D-68, D-64, UI-UX-SPEC section 9: a note every TCVN row of a crop carries (the region note) is said once above those
// rows; any other note stays on its own row, and the two sources' caveats are never mixed. Facts from /api/compare
// (2026-11-14): spring rice of the usual plan and peanut of cc1.
const tcvnNote = {
  vi: 'Chỉ nước tưới dưỡng, không kể nước làm đất. Tiêu chuẩn không nói Nghệ An thuộc Trung bộ hay Bắc bộ.',
  en: 'Maintenance irrigation only, land preparation not included. The standard does not say whether Nghệ An belongs to Trung bộ or Bắc bộ.',
};
const faoNote = { vi: 'Chỉ là ước tính sơ bộ', en: 'Only a rough estimate' };
const fact = (
  measure: 'to_apply' | 'crop_uses',
  value: string,
  unit: string,
  ids: string[],
  scope: string,
  note: typeof faoNote | null,
) => ({
  measure,
  value: { value, unit: { vi: unit, en: unit }, source_ids: ids },
  scope: { vi: scope, en: scope },
  note,
});
const RICE = [
  fact('to_apply', '6,500-7,500', 'm3/ha', ['R-W15'], 'Trung bộ, lúa cấy, vụ xuân', tcvnNote),
  fact('to_apply', '6,500-7,500', 'm3/ha', ['R-W15'], 'Trung bộ, lúa gieo thẳng, vụ xuân', tcvnNote),
  fact('to_apply', '6,000-7,000', 'm3/ha', ['R-W15'], 'Bắc bộ, vụ xuân', tcvnNote),
  fact('crop_uses', '450-700', 'mm', ['R-M02'], 'Lúa nước, cả thời gian sinh trưởng', faoNote),
];
const PEANUT = [
  fact('to_apply', '2,000', 'm3/ha', ['R-W15'], 'Trung bình', null),
  fact('crop_uses', '500-700', 'mm', ['R-M02'], 'Cả thời gian sinh trưởng', faoNote),
];

function waterRow(facts: typeof RICE): Element {
  const res = validateCompare(compare(), body);
  const plan = res.plans[2];
  const key = plan?.calendar[0]?.crop_key;
  if (!plan || !key) throw new Error('no plan');
  res.sources = {
    ...res.sources,
    'R-W15': { ...res.sources['R-P02'], id: 'R-W15' },
    'R-M02': { ...res.sources['R-P02'], id: 'R-M02' },
  } as typeof res.sources;
  plan.water = facts.map((w) => ({ ...w, crop_key: key }));
  render(
    <SettingsProvider>
      <ProvenanceProvider>
        <PlanCard plan={plan} res={res} priority="income" own={own} onShare={async () => true} />
      </ProvenanceProvider>
    </SettingsProvider>,
  );
  const row = document.querySelector(`[data-testid="card-${plan.id}-row-water"]`);
  if (!row) throw new Error('no water row');
  return row;
}

// D-187 (F2): the water row keeps the lead, the value and the scope of each fact; each note opens with its own
// source's values, so the TCVN and FAO caveats still never mix
describe('water notes', () => {
  afterEach(cleanup);
  it('keep the scopes on the row and the notes off it', () => {
    const text = waterRow(RICE).textContent ?? '';
    for (const scope of ['Trung bộ, lúa cấy, vụ xuân', 'Bắc bộ, vụ xuân', 'Lúa nước, cả thời gian sinh trưởng'])
      expect(text).toContain(scope);
    for (const note of [tcvnNote.vi, faoNote.vi]) expect(text).not.toContain(note);
  });
  it('open the TCVN note with each TCVN value and the FAO note with the FAO value only', () => {
    const tcvn = sheetOf('6.000-7.000 m³/ha', waterRow(RICE));
    expect(tcvn).toContain(tcvnNote.vi);
    expect(tcvn).not.toContain(faoNote.vi);
    cleanup();
    const fao = sheetOf('450-700 mm', waterRow(RICE));
    expect(fao).toContain(faoNote.vi);
    expect(fao).not.toContain(tcvnNote.vi);
    expect(fao).not.toContain(vi.farmer.rows.waterNote);
  });
  it('never put the FAO caveat in the sheet of a TCVN value', () => {
    expect(sheetOf('2.000 m³/ha', waterRow(PEANUT))).not.toContain(faoNote.vi);
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
      // D-187: the line that says what the weather shares are sits with the tables it explains
      if (row === 'weather') expect(panel?.textContent).toContain(vi.farmer.rows.weatherNote);
      expect(panel?.hasAttribute('hidden'), row).toBe(false); // hidden by screen-only CSS, so print shows it (T35)
      button?.click();
      await Promise.resolve();
      expect(button?.getAttribute('aria-expanded'), row).toBe('true');
    }
  });
});

// D-172: under the plan name, the card's money total and where its water facts are, each reusing the card's values.
// Values from /api/compare (2026-11-15): the usual plan's total and the P-03 season values of usual_p03.
describe('card summary', () => {
  afterEach(cleanup);
  const head = (planIndex: number) => {
    const res = validateCompare(compare(), body);
    const usual = res.plans[0];
    const p03 = res.plans[1];
    if (!usual || !p03) throw new Error('no plan');
    usual.money.total = {
      value: '30,799',
      unit: { vi: 'nghìn đồng/ha', en: 'thousand VND/ha' },
      source_ids: ['R-P02', 'E-022'],
    };
    p03.money = { ...p03.money, items: [], total: null, season_values: P03_SEASONS };
    res.sources = { ...res.sources, 'E-022': { ...res.sources['R-P02'], id: 'E-022' } } as typeof res.sources;
    const plan = res.plans[planIndex];
    if (!plan) throw new Error('no plan');
    render(
      <SettingsProvider>
        <ProvenanceProvider>
          <PlanCard plan={plan} res={res} priority="income" own={own} onShare={async () => true} />
        </ProvenanceProvider>
      </SettingsProvider>,
    );
    const box = document.querySelector(`[data-testid="card-${plan.id}-row-header"]`);
    if (!box) throw new Error('no head');
    return { box, id: plan.id };
  };
  it('shows the money total with its label, its source button and the trial wording', () => {
    const { box } = head(0);
    const text = box.textContent ?? '';
    expect(text).toContain(vi.farmer.rows.money);
    expect(text).toContain(vi.farmer.own.yearSum);
    expect(text).not.toContain(vi.farmer.ourSum); // D-187: the long wording opens with the total
    const button = box.querySelector('[data-value="30.799 nghìn đồng/ha"]');
    expect(button?.tagName).toBe('BUTTON');
  });
  it('shows the P-03 money of each season with its source button, with no total', () => {
    const { box } = head(1);
    for (const shown of ['5,36 triệu đồng/ha', '1,16 triệu đồng/ha', 'Vụ Thu Đông: bỏ hoang.'])
      expect(box.querySelector(`button[data-value="${shown}"]`), shown).not.toBeNull();
    expect(box.textContent).not.toContain(vi.farmer.own.yearSum);
    expect(box.textContent).not.toContain('30.799');
  });
  it('keeps a link to the water row', () => {
    for (const i of [0, 1]) {
      const { box, id } = head(i);
      const link = box.querySelector(`a[href="#card-${id}-row-water"]`);
      expect(link?.textContent, id).toBe(vi.farmer.summaryWater(vi.farmer.rows.water));
      expect(document.getElementById(`card-${id}-row-water`), id).not.toBeNull();
      cleanup();
    }
  });
  // review of PR #54: a keyboard or screen-reader user lands on the water row, not only the screen
  it('moves the focus to the water row it scrolls to', () => {
    const scroll = mock.fn();
    const before = Element.prototype.scrollIntoView;
    Element.prototype.scrollIntoView = scroll;
    onTestFinished(() => {
      Element.prototype.scrollIntoView = before;
    });
    const { box, id } = head(0);
    const link = box.querySelector(`a[href="#card-${id}-row-water"]`);
    if (!(link instanceof HTMLElement)) throw new Error('no link');
    fireEvent.click(link);
    const row = document.getElementById(`card-${id}-row-water`);
    expect(scroll).toHaveBeenCalledTimes(1);
    expect(document.activeElement).toBe(row);
    expect(row?.getAttribute('tabindex')).toBe('-1');
    // D-187 item 4: the water row folds, so the link opens it
    expect(row?.querySelector('h3 > button')?.getAttribute('aria-expanded')).toBe('true');
  });
});

// FR-15 and D-172: each of the four why parts gets an "explain simply" button when the server has the feature on; the
// reply shows under its part, marked as AI-generated (R-H15). Fetch is mocked: no test reaches the real API.
describe('explain simply', () => {
  afterEach(() => {
    cleanup();
    mock.unstubAllGlobals();
  });
  function ToEnglish() {
    const { setLang } = useSettings();
    return (
      <button type="button" onClick={() => setLang('en')}>
        to-en
      </button>
    );
  }
  const card = (explain: boolean) => {
    const res = validateCompare(compare(), body);
    const plan = res.plans[2];
    if (!plan) throw new Error('no plan');
    render(
      <SettingsProvider>
        <ProvenanceProvider>
          <ToEnglish />
          <PlanCard plan={plan} res={res} priority="income" explain={explain} own={own} onShare={async () => true} />
        </ProvenanceProvider>
      </SettingsProvider>,
    );
    const row = document.querySelector(`[data-testid="card-${plan.id}-row-why"]`);
    if (!row) throw new Error('no why row');
    return { row: within(row as HTMLElement), res, plan };
  };
  const answer = (status: number, json: unknown) => {
    const fetchMock = mock.fn(async () => new Response(JSON.stringify(json), { status }));
    mock.stubGlobal('fetch', fetchMock);
    return fetchMock;
  };

  it('has no button while the feature is off', () => {
    const { row } = card(false);
    expect(row.queryAllByRole('button', { name: new RegExp(vi.farmer.explain.button) })).toHaveLength(0);
  });
  it('gives each of the four parts its own named button', () => {
    const { row } = card(true);
    const buttons = row.getAllByRole('button', { name: new RegExp(vi.farmer.explain.button) });
    expect(buttons.map((b) => b.textContent)).toEqual(
      (['why', 'evidence', 'benefits', 'gaps'] as const).map(
        (k) => `${vi.farmer.explain.button}: ${vi.farmer.whyParts[k]}`,
      ),
    );
  });
  it('asks for the part and shows the reply under it, marked as AI-generated', async () => {
    const fetchMock = answer(200, { text: 'Lời dễ hiểu', ai_generated: true, model: 'claude-haiku-5-5' });
    const { row, res, plan } = card(true);
    fireEvent.click(row.getByRole('button', { name: new RegExp(vi.farmer.whyParts.evidence) }));
    expect(row.getByText(vi.farmer.explain.loading)).not.toBeNull();
    expect(await row.findByText('Lời dễ hiểu')).not.toBeNull();
    expect(row.getByText(vi.farmer.explain.aiLabel)).not.toBeNull();
    expect(fetchMock).toHaveBeenCalledWith(
      '/api/explain',
      expect.objectContaining({
        body: JSON.stringify({ answers: res.request, plan: plan.id, field: 'evidence', lang: 'vi' }),
      }),
    );
  });
  // review of PR #54: a reply in Vietnamese never stays under the English text
  it('drops the reply and shows the button again when the language changes', async () => {
    answer(200, { text: 'Lời dễ hiểu', ai_generated: true, model: 'claude-haiku-5-5' });
    const { row } = card(true);
    fireEvent.click(row.getByRole('button', { name: new RegExp(vi.farmer.whyParts.evidence) }));
    expect(await row.findByText('Lời dễ hiểu')).not.toBeNull();
    fireEvent.click(within(document.body).getByRole('button', { name: 'to-en' }));
    expect(row.queryByText('Lời dễ hiểu')).toBeNull();
    expect(row.queryByText(en.farmer.explain.aiLabel)).toBeNull();
    expect(
      row.getByRole('button', { name: new RegExp(`${en.farmer.explain.button}: ${en.farmer.whyParts.evidence}`) }),
    ).not.toBeNull();
  });
  // review of PR #54: a 502 also covers timeouts, rate limits and the spend limit, so the text names no cause
  it('says only that the part could not be reworded on a 502', async () => {
    answer(502, { detail: 'Bad Gateway' });
    const { row } = card(true);
    // the row's own heading button also starts with "Vì sao", so the name starts with the explain button's text
    fireEvent.click(
      row.getByRole('button', { name: new RegExp(`^${vi.farmer.explain.button}.*${vi.farmer.whyParts.why}`) }),
    );
    expect(await row.findByText('Không viết lại được đoạn này. Hãy đọc đoạn gốc ở trên.')).not.toBeNull();
    expect(en.farmer.explain.refused).toBe('Could not reword this part. Please read the text above.');
  });
  it.each([
    [502, 'refused'],
    [503, 'busy'],
    [500, 'failed'],
  ] as const)('says what happened on a %i and keeps the button', async (status, key) => {
    answer(status, { detail: 'x' });
    const { row } = card(true);
    fireEvent.click(row.getByRole('button', { name: new RegExp(vi.farmer.whyParts.gaps) }));
    expect(await row.findByText(vi.farmer.explain[key])).not.toBeNull();
    expect(row.queryByText(vi.farmer.explain.aiLabel)).toBeNull();
    expect(row.getByRole('button', { name: new RegExp(vi.farmer.whyParts.gaps) })).not.toBeNull();
  });
});

// D-175: per crop, the lowest to the highest of its TCVN 8641 rows, labelled "by region", with the TCVN source; FAO
// stays out. Rows from /api/compare (2026-11-15) for the usual plan (spring rice: Trung bộ x2 and Bắc bộ, then an FAO
// row; black bean not listed; sweet potato one row) and cc1 (peanut one row and an FAO row; mung bean not listed).
describe('card head water line', () => {
  afterEach(cleanup);
  const m3 = { vi: 'm3/ha', en: 'm3/ha' };
  const mm = { vi: 'mm', en: 'mm' };
  // the note every TCVN rice row carries (rules/crops.yaml)
  const RICE_NOTE = {
    vi: 'Chỉ nước tưới dưỡng, không kể nước làm đất. Tiêu chuẩn không nói Nghệ An thuộc Trung bộ hay Bắc bộ.',
    en: 'Maintenance irrigation only, land preparation not included. The standard does not say whether Nghệ An belongs to Trung bộ or Bắc bộ.',
  };
  type Row = [string, 'to_apply' | 'crop_uses' | 'not_listed', string | null, typeof RICE_NOTE?];
  const PLANS: Record<string, { crops: [string, string][]; water: Row[] }> = {
    usual: {
      crops: [
        ['usual_spring_rice', 'Lúa'],
        ['usual_summer_autumn_black_bean', 'Đậu đen xanh lòng'],
        ['usual_autumn_winter_sweet_potato', 'Khoai lang'],
      ],
      water: [
        ['usual_spring_rice', 'to_apply', '6,500-7,500', RICE_NOTE],
        ['usual_spring_rice', 'to_apply', '6,500-7,500', RICE_NOTE],
        ['usual_spring_rice', 'to_apply', '6,000-7,000', RICE_NOTE],
        ['usual_spring_rice', 'crop_uses', '450-700'],
        ['usual_summer_autumn_black_bean', 'not_listed', null],
        ['usual_autumn_winter_sweet_potato', 'to_apply', '1,200-1,400'],
      ],
    },
    cc1: {
      crops: [
        ['cc1_spring_peanut', 'Lạc'],
        ['cc1_summer_autumn_mung_bean', 'Đậu xanh'],
      ],
      water: [
        ['cc1_spring_peanut', 'to_apply', '2,000'],
        ['cc1_spring_peanut', 'crop_uses', '500-700'],
        ['cc1_summer_autumn_mung_bean', 'not_listed', null],
      ],
    },
  };
  const line = (id: 'usual' | 'cc1', languages = ['vi-VN', 'vi']) => {
    Object.defineProperty(window.navigator, 'languages', { value: languages, configurable: true });
    const res = validateCompare(compare(), body);
    const plan = res.plans.find((p) => p.id === id);
    const base = plan?.calendar[0];
    if (!plan || !base) throw new Error('no plan');
    const { crops, water } = PLANS[id] ?? { crops: [], water: [] };
    plan.calendar = crops.map(([key, name]) => ({ ...base, crop_key: key, crop: { vi: name, en: name } }));
    plan.water = water.map(([key, measure, v, note]) => ({
      crop_key: key,
      measure,
      value:
        v === null
          ? null
          : {
              value: v,
              unit: measure === 'crop_uses' ? mm : m3,
              source_ids: [measure === 'crop_uses' ? 'R-M02' : 'R-W15'],
            },
      scope: null,
      note: note ?? null,
    }));
    res.sources = {
      ...res.sources,
      'R-W15': { ...res.sources['R-P02'], id: 'R-W15', citation: { vi: 'TCVN 8641:2011', en: 'TCVN 8641:2011' } },
      'R-M02': { ...res.sources['R-P02'], id: 'R-M02' },
    } as typeof res.sources;
    render(
      <SettingsProvider>
        <ProvenanceProvider>
          <PlanCard plan={plan} res={res} priority="income" own={own} onShare={async () => true} />
        </ProvenanceProvider>
      </SettingsProvider>,
    );
    const box = document.querySelector(`[data-testid="card-${id}-water-line"]`);
    if (!box) throw new Error('no water line');
    const values = [...box.querySelectorAll('button[data-value]')].map((e) => e.getAttribute('data-value'));
    return { text: box.textContent ?? '', values };
  };
  it('spans the TCVN rows of each crop, says no figure without one and leaves FAO out (usual plan)', () => {
    const { text, values } = line('usual');
    expect(text.startsWith(`${vi.farmer.summaryWaterLabel}:`)).toBe(true);
    expect(text).not.toContain('TCVN'); // D-187: the standard's name and the range note open with the range
    expect(values).toEqual(['6.000-7.500 m³/ha', '1.200-1.400 m³/ha']);
    expect(text.indexOf('Lúa')).toBeLessThan(text.indexOf('Đậu đen xanh lòng'));
    expect(text.indexOf('Đậu đen xanh lòng')).toBeLessThan(text.indexOf('Khoai lang'));
    expect(text).toContain('Đậu đen xanh lòng: nguồn không có số');
    expect(text).not.toContain('450');
  });
  // second review of PR #54: without the rice note the head's range reads lower than the water a farmer needs
  it("says the rice rows' shared TCVN note, short, right after the rice range", () => {
    const { text } = line('usual');
    const range = text.indexOf('6.000-7.500');
    const note = text.indexOf('(Chỉ nước tưới dưỡng, không kể nước làm đất.)');
    expect(note).toBeGreaterThan(range);
    expect(note).toBeLessThan(text.indexOf('Đậu đen xanh lòng'));
    expect(text).not.toContain('Tiêu chuẩn không nói');
    expect(text.split('Chỉ nước tưới dưỡng')).toHaveLength(2);
  });
  it('shows the one TCVN value of peanut (cc1), in English as given', () => {
    expect(line('cc1').values).toEqual(['2.000 m³/ha']);
    cleanup();
    const english = line('cc1', ['en-GB', 'en']);
    expect(english.values).toEqual(['2,000 m³/ha']);
    expect(english.text).toContain('Đậu xanh: no figure in the source');
    expect(english.text.startsWith(`${en.farmer.summaryWaterLabel}:`)).toBe(true);
    Object.defineProperty(window.navigator, 'languages', { value: ['vi-VN', 'vi'], configurable: true });
  });
  it('opens the range note and the whole rice note with the range', () => {
    line('usual');
    const sheet = sheetOf('6.000-7.500 m³/ha');
    for (const note of [vi.farmer.summaryWaterNote, RICE_NOTE.vi, vi.farmer.rows.waterNote])
      expect(sheet).toContain(note);
  });
  it('opens the TCVN source of the rows it spans', () => {
    line('usual');
    const button = [...document.querySelectorAll('button[data-value]')].find(
      (e) => e.getAttribute('data-value') === '6.000-7.500 m³/ha',
    );
    if (!(button instanceof HTMLElement)) throw new Error('no button');
    expect(document.body.textContent).not.toContain('TCVN 8641:2011');
    fireEvent.click(button);
    expect(document.body.textContent).toContain('TCVN 8641:2011');
  });
});

// D-187 (roleplay audit 2026-11-15, F4): each risk quote is one plain line with its source in a few words; the full
// quote opens in the source sheet. Quotes: the rulebook's risk lines of cc2 (rules/rotations.yaml).
describe('considerations', () => {
  afterEach(cleanup);
  const checks = (risks: { text: { vi: string; en: string }; source_ids: string[] }[]) => {
    const res = validateCompare(compare(), body);
    const plan = res.plans.find((p) => p.id === 'cc2');
    if (!plan) throw new Error('no plan');
    plan.why.risks = risks;
    for (const id of ['R-P03', 'R-C13', 'R-G06', 'R-G27'])
      res.sources = { ...res.sources, [id]: { ...res.sources['R-P02'], id } } as typeof res.sources;
    render(
      <SettingsProvider>
        <ProvenanceProvider>
          <PlanCard plan={plan} res={res} priority="income" own={own} onShare={async () => true} />
        </ProvenanceProvider>
      </SettingsProvider>,
    );
    const row = document.querySelector('[data-testid="card-cc2-row-checks"]');
    if (!(row instanceof HTMLElement)) throw new Error('no checks row');
    return row;
  };
  const CC2 = (rulebookPlan('cc2')?.risk_lines ?? []).map((r) => ({ text: r.text, source_ids: [r.source_id] }));
  it('shows one plain line and a short source per quote, not the quote', () => {
    const row = checks(CC2);
    const text = row.textContent ?? '';
    expect(CC2).toHaveLength(6);
    for (const key of ['cost', 'market', 'fodder', 'riceZone', 'stillRice', 'provincePlan'] as const) {
      expect(text).toContain(vi.farmer.considerations[key].line);
      expect(text).toContain(vi.farmer.considerations[key].source);
    }
    for (const r of CC2) expect(text).not.toContain(r.text.vi);
    expect(row.querySelector('h3')?.textContent).toBe('Cần cân nhắc (6)');
  });
  it('opens the full quote with the source button of its line', () => {
    const row = checks(CC2);
    const quote = CC2.find((r) => r.source_ids.includes('R-P03'));
    const item = [...row.querySelectorAll('li')].find((li) =>
      li.textContent?.includes(vi.farmer.considerations.market.line),
    );
    const button = item?.querySelector('button');
    if (!quote || !button) throw new Error('no line');
    fireEvent.click(button);
    const sheet = document.querySelector('[data-testid="source-sheet"]')?.textContent ?? '';
    expect(sheet).toContain(vi.sheet.quote);
    expect(sheet).toContain(quote.text.vi);
  });
  it('shows a quote with no plain line in full', () => {
    const text = checks([
      { text: { vi: 'Một câu trích khác', en: 'Another quote' }, source_ids: ['R-P02'] },
    ]).textContent;
    expect(text).toContain('Một câu trích khác');
  });
});

// D-187 (roleplay audit 2026-11-15, F5): each card lists the questions for the extension officer that the officer
// page shows for the same plan (the API's decision core, data/canonical/decision.json), not new text
describe('questions for the officer', () => {
  afterEach(cleanup);
  const questions = (id: 'usual' | 'cc1') => {
    const res = validateCompare(compare(), body);
    const plan = res.plans.find((p) => p.id === id);
    if (!plan) throw new Error('no plan');
    render(
      <SettingsProvider>
        <ProvenanceProvider>
          <PlanCard plan={plan} res={res} priority="income" own={own} onShare={async () => true} />
        </ProvenanceProvider>
      </SettingsProvider>,
    );
    const row = document.querySelector(`[data-testid="card-${id}-row-checks"]`);
    if (!row) throw new Error('no checks row');
    return [...row.querySelectorAll('ol li')].map((li) => li.textContent);
  };
  // D-191: the trial-field question every plan shares is asked once, in the closing box of the plans page
  const ownQuestions = (id: 'cc1' | 'cc5') =>
    (decisionPlan(id)?.questions_for_officer ?? [])
      .filter((q) => !q.en.includes('like the trial field'))
      .map((q) => q.vi);
  it('lists the officer page questions of the plan, in their order, without the shared trial-field one', () => {
    expect(questions('cc1')).toEqual(ownQuestions('cc1'));
    cleanup();
    expect(questions('usual')).toEqual(ownQuestions('cc5'));
    expect(ownQuestions('cc1').length).toBeGreaterThan(0);
    expect(questions('usual').join(' ')).not.toContain('ruộng thử ở Lưu Sơn');
    expect(vi.farmer.officerQuestions[0]).toContain('ruộng thử nghiệm ở Lưu Sơn');
  });
  it('heads them with the take-to-the-officer label', () => {
    questions('cc1');
    const row = document.querySelector('[data-testid="card-cc1-row-checks"]');
    expect(row?.textContent).toContain(vi.farmer.askOfficer);
    expect(decisionPlan('cc1')?.questions_for_officer.length).toBeGreaterThan(0);
  });
});

// D-192 (screen check of the plans page, 2026-11-15)
describe('screen check details', () => {
  afterEach(cleanup);
  const card = (id: 'usual' | 'cc1' | 'cc2', languages = ['vi-VN', 'vi'], priority: 'income' | 'land' = 'income') => {
    Object.defineProperty(window.navigator, 'languages', { value: languages, configurable: true });
    onTestFinished(() => {
      Object.defineProperty(window.navigator, 'languages', { value: ['vi-VN', 'vi'], configurable: true });
    });
    const res = validateCompare(compare(), body);
    const plan = res.plans.find((p) => p.id === id);
    if (!plan) throw new Error('no plan');
    return { res, plan, priority };
  };
  const show = ({ res, plan, priority }: ReturnType<typeof card>) =>
    render(
      <SettingsProvider>
        <ProvenanceProvider>
          <PlanCard plan={plan} res={res} priority={priority} own={own} onShare={async () => true} />
        </ProvenanceProvider>
      </SettingsProvider>,
    );
  it('points from the bad-weather table to the irrigation row for drought, in both languages', () => {
    show(card('cc1'));
    const fold = document.getElementById('card-cc1-weather-years');
    expect(fold?.firstElementChild?.textContent).toBe('Hạn hán: xem mục “Nước tưới” bên dưới.');
    expect(vi.farmer.rows.water).toBe('Nước tưới');
    cleanup();
    show(card('cc1', ['en-GB', 'en']));
    expect(document.getElementById('card-cc1-weather-years')?.firstElementChild?.textContent).toBe(
      'Drought: see “Irrigation” below.',
    );
    expect(en.farmer.rows.water).toBe('Irrigation');
  });
  it('names each risk source button by the word source and its short line, once', () => {
    const c = card('cc2');
    c.plan.why.risks = (rulebookPlan('cc2')?.risk_lines ?? []).map((r) => ({
      text: r.text,
      source_ids: [r.source_id],
    }));
    for (const id of ['R-P03', 'R-C13', 'R-G06', 'R-G27'])
      c.res.sources = { ...c.res.sources, [id]: { ...c.res.sources['R-P02'], id } } as typeof c.res.sources;
    const view = show(c);
    const line = vi.farmer.considerations.market.line;
    const button = view.getByRole('button', { name: `Nguồn: ${line}` });
    expect(button.textContent).not.toMatch(/Nguồn.*Nguồn/);
  });
  it('says 1 crop, not 1 crops, in English and keeps loại cây in Vietnamese', () => {
    const one = (c: ReturnType<typeof card>) => {
      c.plan.land.crops_in_year.value = { value: '1', unit: { vi: 'loại cây', en: 'crops' }, source_ids: ['R-P02'] };
      return c;
    };
    show(one(card('cc1', ['en-GB', 'en'])));
    const values = () => [...document.querySelectorAll('[data-testid="card-cc1-row-land"] [data-value]')];
    expect(values().map((e) => e.getAttribute('data-value'))).toContain('1 crop');
    cleanup();
    show(one(card('cc1')));
    expect(values().map((e) => e.getAttribute('data-value'))).toContain('1 loại cây');
  });
  it('writes et al. in English where Vietnamese writes và cs.', () => {
    show(card('cc1', ['en-GB', 'en'], 'land'));
    const line = document.querySelector('[data-testid="card-cc1-priority-line"]')?.textContent ?? '';
    expect(line).toContain('Trịnh Đức Toàn et al. 2023');
    expect(line).not.toContain('và cs.');
    cleanup();
    show(card('cc1', ['vi-VN', 'vi'], 'land'));
    expect(document.querySelector('[data-testid="card-cc1-priority-line"]')?.textContent).toContain(
      'Trịnh Đức Toàn và cs. 2023',
    );
  });
});
