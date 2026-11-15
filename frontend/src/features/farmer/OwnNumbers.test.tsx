// UI-UX-SPEC section 12d, D-163: the "your price and costs" form on a plan card. Yields, prices and costs are P-02
// Tables 4 and 12 (peanut 3.91 t/ha, 28,000 đ/kg, cost 83,500; mung bean 1.03 t/ha, 40,000 đ/kg, cost 25,000); the
// results are worked out by hand: 3.91 x 30,000 = 117,300; 1.03 x 45,000 = 46,350; minus 90,000 and 25,000.
import { afterEach, describe, expect, it } from 'vitest';
import { useEffect, useState } from 'react';
import { cleanup, fireEvent, render, screen, within } from '@testing-library/react';
import { SettingsProvider } from '../../app/settings';
import { ProvenanceProvider } from '../provenance/ProvenanceProvider';
import { validateCompare } from '../../api';
import { body, compare, moneyItem } from '../../tests/fixtures';
import { NO_OWN, setOwn, type OwnNumbers } from '../../domain/farmerState';
import type { CompareResponse, Plan } from '../../types';
import { PlanCard } from './PlanCard';
import type { OwnState } from './OwnNumbers';
import { vi } from '../../i18n/vi';
import { en } from '../../i18n/en';

let latest: OwnNumbers = NO_OWN;
const seen = (v: OwnNumbers) => {
  latest = v;
};

function Harness({ plan, res, initial }: { plan: Plan; res: CompareResponse; initial: OwnNumbers }) {
  const [values, setValues] = useState(initial);
  useEffect(() => seen(values), [values]);
  const own: OwnState = { values, set: (field, crop, digits) => setValues((v) => setOwn(v, field, crop, digits)) };
  return <PlanCard plan={plan} res={res} priority="income" own={own} onShare={async () => true} />;
}

function renderForm(initial: OwnNumbers = NO_OWN, items = true) {
  const res = validateCompare(compare(), body);
  const plan = res.plans[2];
  const p02 = res.sources['R-P02'];
  if (!plan || !p02) throw new Error('no plan');
  p02.citation = { vi: 'bài P-02', en: 'paper P-02' };
  // the engine's arithmetic id (D-158), as the server sends it with every computed total
  res.sources = {
    ...res.sources,
    'E-022': { ...p02, id: 'E-022', citation: { vi: 'phép tính E-022', en: 'calculation E-022' } },
  } as typeof res.sources;
  if (items) {
    plan.money.items = [
      { ...moneyItem('cc1_spring_peanut', '3.91', '28,000', '25,980', '83,500'), crop: { vi: 'Lạc', en: 'Peanut' } },
      {
        ...moneyItem('cc1_summer_autumn_mung_bean', '1.03', '40,000', '16,200', '25,000'),
        crop: { vi: 'Đậu xanh', en: 'Mung bean' },
      },
    ];
  }
  render(
    <SettingsProvider>
      <ProvenanceProvider>
        <Harness plan={plan} res={res} initial={initial} />
      </ProvenanceProvider>
    </SettingsProvider>,
  );
  return plan.id;
}

const open = () => fireEvent.click(screen.getByRole('button', { name: vi.farmer.yourNumbers }));
const field = (name: RegExp) => screen.getByRole('spinbutton', { name });
const type = (name: RegExp, value: string) => fireEvent.change(field(name), { target: { value } });
const ownBox = (id: string) => {
  const box = document.querySelector(`[data-testid="card-${id}-own"]`);
  if (!(box instanceof HTMLElement)) throw new Error('no result box');
  return box;
};
const result = (id: string) => ownBox(id).textContent;

describe('your price and costs', () => {
  afterEach(() => {
    cleanup();
    latest = NO_OWN;
  });

  it('opens a form with a number field for the price and the cost of each crop', () => {
    renderForm();
    const button = screen.getByRole('button', { name: vi.farmer.yourNumbers });
    expect(button.getAttribute('aria-expanded')).toBe('false');
    open();
    expect(button.getAttribute('aria-expanded')).toBe('true');
    const inputs = [...document.querySelectorAll('input')];
    expect(inputs).toHaveLength(4);
    for (const input of inputs) {
      expect(input.getAttribute('type')).toBe('number'); // H4, T4: numeric input only, no text field
      expect(input.value).toBe(''); // empty is allowed
    }
    expect(field(/^Lạc.*Giá bán của bạn \(đồng\/kg\)$/).getAttribute('inputmode')).toBe('numeric');
    // D-192: the cost in million đ/ha like the money shown (D-190), so a decimal key
    expect(field(/^Lạc.*Chi phí của bạn \(triệu đồng\/ha\)$/).getAttribute('inputmode')).toBe('decimal');
  });

  it('shows the study yield and price next to the fields, with their source buttons', () => {
    renderForm();
    open();
    const values = [...document.querySelectorAll('[data-value]')].map((e) => e.getAttribute('data-value'));
    expect(values).toEqual(expect.arrayContaining(['3,91 tấn/ha', '28.000 đồng/kg', '1,03 tấn/ha', '40.000 đồng/kg']));
  });

  it('works out revenue from the price and the margin only once a cost is typed, labelled as your numbers', () => {
    const id = renderForm();
    open();
    type(/^Đậu xanh.*Giá bán/, '45000');
    expect(latest.prices).toEqual({ cc1_summer_autumn_mung_bean: '45000' });
    expect(result(id)).toContain(vi.farmer.yourNumbersLabel);
    expect(result(id)).toContain(`${vi.farmer.own.revenue}: 46,4 triệu đồng/ha`);
    expect(result(id)).not.toContain(vi.farmer.own.margin);
    expect(result(id)).toContain(vi.farmer.own.needPrice); // peanut has no price yet
    type(/^Đậu xanh.*Chi phí/, '25');
    expect(result(id)).toContain(`${vi.farmer.own.margin}: 21,4 triệu đồng/ha`);
    expect(result(id)).not.toContain(vi.farmer.own.yearSum); // no partial whole-year sum
  });

  it('adds the whole year once every crop has its numbers', () => {
    const id = renderForm();
    open();
    type(/^Lạc.*Giá bán/, '30000');
    type(/^Đậu xanh.*Giá bán/, '45000');
    expect(result(id)).toContain(vi.farmer.own.yearSum);
    expect(result(id)).toContain('163,7 triệu đồng/ha'); // 117,300 + 46,350 thousand, in million (D-190)
    type(/^Lạc.*Chi phí/, '90');
    type(/^Đậu xanh.*Chi phí/, '25');
    expect(result(id)).toContain('48,7 triệu đồng/ha'); // 27,300 + 21,350 thousand, in million (D-190)
  });

  it('does not use a number that is not whole and says so', () => {
    const id = renderForm();
    open();
    type(/^Đậu xanh.*Giá bán/, '1.5');
    expect(screen.getByText(vi.farmer.own.invalid)).toBeTruthy();
    expect(field(/^Đậu xanh.*Giá bán/).getAttribute('aria-invalid')).toBe('true');
    expect(latest.prices).toEqual({});
    expect(result(id)).not.toContain(vi.farmer.own.revenue);
  });

  it('does not use a number longer than 9 digits and says so (D-179)', () => {
    const id = renderForm();
    open();
    type(/^Đậu xanh.*Giá bán/, '1234567890');
    expect(screen.getByText(vi.farmer.own.invalid)).toBeTruthy();
    expect(vi.farmer.own.invalid).toContain('9 chữ số');
    expect(en.farmer.own.invalid).toContain('9 digits');
    expect(latest.prices).toEqual({});
    expect(result(id)).not.toContain(vi.farmer.own.revenue);
  });

  it('keeps the study money row as it was', () => {
    const id = renderForm();
    open();
    type(/^Lạc.*Giá bán/, '30000');
    const row = document.querySelector(`[data-testid="card-${id}-row-money"]`);
    if (!(row instanceof HTMLElement)) throw new Error('no money row');
    for (const v of ['26,0 triệu đồng/ha', '83,5 triệu đồng/ha']) expect(within(row).getAllByText(v).length).toBe(1);
  });

  it('opens with the numbers already in the link, and its sheet names the study yield and your own numbers', () => {
    const id = renderForm({ prices: { cc1_spring_peanut: '30000' }, costs: {} });
    expect(field(/^Lạc.*Giá bán/)).toHaveProperty('value', '30000');
    fireEvent.click(within(ownBox(id)).getByRole('button', { name: /^117,3 triệu đồng\/ha/ }));
    const sheet = screen.getByTestId('source-sheet').textContent;
    expect(sheet).toContain('117.300 nghìn đồng/ha'); // the sheet keeps the exact value and unit (D-190)
    expect(sheet).toContain('bài P-02'); // the study yield's source
    expect(sheet).toContain('phép tính E-022'); // a number we compute cites its inputs and E-022 (D-158)
    expect(sheet).toContain(vi.farmer.own.sheetNote);
  });

  // D-192: typed in million đ/ha, kept in thousand đ/ha in the link and a saved set (D-180), as before
  it('keeps a cost typed in million as thousand and shows a kept one back in million', () => {
    renderForm({ prices: {}, costs: { cc1_spring_peanut: '24700' } });
    expect(field(/^Lạc.*Chi phí/)).toHaveProperty('value', '24.7');
    type(/^Đậu xanh.*Chi phí/, '24.689');
    expect(latest.costs).toEqual({ cc1_spring_peanut: '24700', cc1_summer_autumn_mung_bean: '24689' });
  });

  it('does not use a cost below 0 or above the limit and says so', () => {
    renderForm();
    open();
    for (const bad of ['-3', '1000000']) {
      type(/^Đậu xanh.*Chi phí/, bad);
      expect(screen.getByText(vi.farmer.own.invalidCost)).toBeTruthy();
      expect(field(/^Đậu xanh.*Chi phí/).getAttribute('aria-invalid')).toBe('true');
      expect(latest.costs).toEqual({});
    }
  });

  it('is not offered on a card without per-crop money (P-03)', () => {
    renderForm(NO_OWN, false);
    expect(screen.queryByRole('button', { name: vi.farmer.yourNumbers })).toBeNull();
  });
});
