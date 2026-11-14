// UI-UX-SPEC section 14a test hooks with member B's row names (D-169): card-<plan id> and card-<plan id>-row-<row>.
import { afterEach, describe, expect, it, vi as mock } from 'vitest';
import { cleanup, fireEvent, render, within } from '@testing-library/react';
import { SettingsProvider, useSettings } from '../../app/settings';
import { ProvenanceProvider } from '../provenance/ProvenanceProvider';
import { validateCompare } from '../../api';
import { body, compare } from '../../tests/fixtures';
import { PlanCard } from './PlanCard';
import { vi } from '../../i18n/vi';
import { en } from '../../i18n/en';

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

function waterText(facts: typeof RICE): string {
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
        <PlanCard plan={plan} res={res} priority="income" onShare={async () => true} />
      </ProvenanceProvider>
    </SettingsProvider>,
  );
  return document.querySelector(`[data-testid="card-${plan.id}-row-water"]`)?.textContent ?? '';
}

describe('water notes', () => {
  afterEach(cleanup);
  it('say the TCVN region note once above the TCVN rows and keep the FAO note on the FAO row', () => {
    const text = waterText(RICE);
    expect(text.split(tcvnNote.vi)).toHaveLength(2);
    expect(text.indexOf(tcvnNote.vi)).toBeLessThan(text.indexOf('Trung bộ, lúa cấy, vụ xuân'));
    expect(text.split(faoNote.vi)).toHaveLength(2);
    expect(text.indexOf(faoNote.vi)).toBeGreaterThan(text.indexOf('Lúa nước, cả thời gian sinh trưởng'));
  });
  it('never puts the FAO caveat above a TCVN row', () => {
    const text = waterText(PEANUT);
    expect(text.indexOf(faoNote.vi)).toBeGreaterThan(text.indexOf('Cả thời gian sinh trưởng'));
    expect(text.indexOf(faoNote.vi)).toBeGreaterThan(text.indexOf('Trung bình'));
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

// D-172: under the plan name, the card's money total and where its water facts are, each reusing the card's values.
// Values from /api/compare (2026-11-15): the usual plan's total and the P-03 text of usual_p03.
describe('card summary', () => {
  afterEach(cleanup);
  const P03_TEXT = {
    vi: 'Lúa vụ Đông Xuân 2021 (đối chứng): hiệu quả kinh tế 5,36 triệu đồng/ha. Lúa vụ Hè Thu 2020 (đối chứng): "gần như không có lợi nhuận, hiệu quả kinh tế chỉ đạt 1,16 triệu/ha". Vụ Thu Đông: bỏ hoang.',
    en: 'Spring-season rice 2021 (control): economic return ("hiệu quả kinh tế") 5.36 million đ/ha. Summer-autumn rice 2020 (control): "almost no profit, the economic return only reaches 1.16 million/ha" (our translation). Autumn-winter: fallow.',
  };
  const head = (planIndex: number) => {
    const res = validateCompare(compare(), body);
    const usual = res.plans[0];
    const p03 = res.plans[1];
    if (!usual || !p03) throw new Error('no plan');
    usual.money.total = {
      value: '30,799',
      unit: { vi: 'nghìn đồng/ha', en: 'thousand đ/ha' },
      source_ids: ['R-P02', 'E-022'],
    };
    p03.money = { ...p03.money, items: [], total: null, text_only: P03_TEXT };
    res.sources = { ...res.sources, 'E-022': { ...res.sources['R-P02'], id: 'E-022' } } as typeof res.sources;
    const plan = res.plans[planIndex];
    if (!plan) throw new Error('no plan');
    render(
      <SettingsProvider>
        <ProvenanceProvider>
          <PlanCard plan={plan} res={res} priority="income" onShare={async () => true} />
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
    expect(text).toContain(vi.farmer.ourSum);
    const button = box.querySelector('[data-value="30.799 nghìn đồng/ha"]');
    expect(button?.tagName).toBe('BUTTON');
  });
  it('shows the P-03 money as its text only, with no total', () => {
    const { box } = head(1);
    const button = [...box.querySelectorAll('[data-value]')].find((e) => e.getAttribute('data-value') === P03_TEXT.vi);
    expect(button?.tagName).toBe('BUTTON');
    expect(box.textContent).not.toContain(vi.farmer.ourSum);
    expect(box.textContent).not.toContain('30.799');
  });
  it('points to the water row without a number of its own', () => {
    for (const i of [0, 1]) {
      const { box, id } = head(i);
      const link = box.querySelector(`a[href="#card-${id}-row-water"]`);
      expect(link?.textContent, id).toBe(vi.farmer.summaryWater(vi.farmer.rows.water));
      expect(link?.textContent ?? '', id).not.toMatch(/\d/);
      expect(document.getElementById(`card-${id}-row-water`), id).not.toBeNull();
      cleanup();
    }
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
          <PlanCard plan={plan} res={res} priority="income" explain={explain} onShare={async () => true} />
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
