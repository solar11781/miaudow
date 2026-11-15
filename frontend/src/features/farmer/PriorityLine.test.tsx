// UI-UX-SPEC section 9 priority highlight (bonus, D-139) and D-136: the priority line of cards cc1..cc4.
import { afterEach, describe, expect, it } from 'vitest';
import { cleanup, render } from '@testing-library/react';
import { SettingsProvider } from '../../app/settings';
import { ProvenanceProvider } from '../provenance/ProvenanceProvider';
import { validateCompare } from '../../api';
import { body, compare } from '../../tests/fixtures';
import { PlanCard } from './PlanCard';
import { NO_OWN } from '../../domain/farmerState';
import { vi } from '../../i18n/vi';
import { SOURCES } from '../../domain/sources';
import type { CompareResponse, Plan, PlanId, Priority } from '../../types';

const own = { values: NO_OWN, set: () => undefined };
const PRIORITIES: Priority[] = ['income', 'stability', 'water', 'land'];
// UI-UX-SPEC T37 and D-136: never better, best, should or recommended, nor their Vietnamese equivalents (glossary)
const BANNED =
  /better|best|should|recommend|propos|suitable|more profitable|tốt hơn|tốt nhất|\bnên\b|khuyến nghị|khuyên|đề xuất|đề nghị|phù hợp|lãi hơn/i;
const unit = (vi: string, en: string) => ({ vi, en });
const v = (value: string, u: { vi: string; en: string }) => ({ value, unit: u, source_ids: ['R-P02'] });

// values as /api/compare gives them (2026-11-15) for the usual plan and cc1
function response(): CompareResponse {
  const res = validateCompare(compare(), body);
  const set = (id: PlanId, total: string, crops: string, days: string | null, name: string) => {
    const p = res.plans.find((x) => x.id === id);
    if (!p) throw new Error(id);
    p.name = { vi: name, en: name };
    p.money.total = v(total, unit('nghìn đồng/ha', 'thousand đ/ha'));
    p.land.crops_in_year = { ...p.land.crops_in_year, value: v(crops, unit('loại cây', 'crops')) };
    p.land.living_days = { ...p.land.living_days, value: days ? v(days, unit('ngày', 'days')) : null };
  };
  set('usual', '30,799', '3', '309', 'Lúa Khang dân - Đậu đen xanh lòng VT1 - Khoai lang Chiêm Dâu');
  set('cc1', '53,380', '3', '311', 'Lạc L20 - Đậu xanh D22 - Ngô thương phẩm VN5885');
  return res;
}

function card(res: CompareResponse, id: PlanId, priority: Priority) {
  const plan = res.plans.find((p) => p.id === id);
  if (!plan) throw new Error(id);
  const ui = (pr: Priority, p: Plan = plan) => (
    <SettingsProvider>
      <ProvenanceProvider>
        <PlanCard plan={p} res={res} priority={pr} own={own} onShare={async () => true} />
      </ProvenanceProvider>
    </SettingsProvider>
  );
  const view = render(ui(priority));
  return { rerender: (pr: Priority) => view.rerender(ui(pr)) };
}

const line = (id: PlanId) => document.querySelector(`[data-testid="card-${id}-priority-line"]`);
const values = (el: Element | null) =>
  [...(el?.querySelectorAll('button[data-value]') ?? [])].map((b) => b.getAttribute('data-value'));

describe('priority line', () => {
  afterEach(cleanup);
  it('T37 sits inside the highlighted row, right after the label, on cc1..cc4 only', () => {
    for (const id of ['cc1', 'cc2', 'cc3', 'cc4'] as const)
      for (const pr of PRIORITIES) {
        card(response(), id, pr);
        const el = line(id);
        expect(el?.closest('[data-highlighted="true"]'), `${id} ${pr}`).not.toBeNull();
        expect(el?.previousElementSibling?.textContent).toContain(vi.farmer.yourPriority);
        cleanup();
      }
    for (const id of ['usual', 'usual_p03'] as const)
      for (const pr of PRIORITIES) {
        card(response(), id, pr);
        expect(document.querySelector('[data-testid$="-priority-line"]'), `${id} ${pr}`).toBeNull();
        cleanup();
      }
  });
  it("T37 income shows this card's money total and the usual card's, each a source button", () => {
    card(response(), 'cc1', 'income');
    expect(values(line('cc1'))).toEqual(['53.380 nghìn đồng/ha', '30.799 nghìn đồng/ha']);
    expect(line('cc1')?.textContent).toContain('Lúa Khang dân - Đậu đen xanh lòng VT1 - Khoai lang Chiêm Dâu');
    // shown in million dong per ha (D-190); the source buttons keep the exact values above
    expect(line('cc1')?.textContent).toContain('53,4 triệu đồng/ha');
    expect(line('cc1')?.textContent).toContain('30,8 triệu đồng/ha');
  });
  it("T37 land shows this card's and the usual card's crops in the year and living days", () => {
    card(response(), 'cc1', 'land');
    expect(values(line('cc1'))).toEqual(['3 loại cây', '3 loại cây', '311 ngày', '309 ngày']);
    expect(line('cc1')?.textContent).toContain(vi.farmer.cropsInYear);
    expect(line('cc1')?.textContent).toContain(vi.farmer.livingDays);
  });
  it('says not available for a null value', () => {
    const res = response();
    const usual = res.plans.find((p) => p.id === 'usual');
    if (usual) usual.land.living_days = { ...usual.land.living_days, value: null };
    card(res, 'cc1', 'land');
    expect(values(line('cc1'))).toEqual(['3 loại cây', '3 loại cây', '311 ngày']);
    expect(line('cc1')?.textContent).toContain(vi.common.notAvailable);
  });
  it('points stability and water to the same row on the usual card, with no numbers', () => {
    for (const pr of ['stability', 'water'] as const) {
      card(response(), 'cc1', pr);
      expect(values(line('cc1'))).toEqual([]);
      expect(line('cc1')?.textContent).toContain('Lúa Khang dân - Đậu đen xanh lòng VT1 - Khoai lang Chiêm Dâu');
      cleanup();
    }
  });
  it('T37 names P-02 by its short name and never says better, best, should or recommended, in either language', () => {
    for (const languages of [
      ['vi-VN', 'vi'],
      ['en-GB', 'en'],
    ]) {
      Object.defineProperty(window.navigator, 'languages', { value: languages, configurable: true });
      for (const pr of PRIORITIES) {
        card(response(), 'cc1', pr);
        expect(line('cc1')?.textContent, `${languages[0]} ${pr}`).not.toMatch(BANNED);
        // P-02, not the author line it shares with P-03 (D-52)
        expect(line('cc1')?.textContent, `${languages[0]} ${pr}`).toContain(SOURCES.p02.short);
        cleanup();
      }
    }
    Object.defineProperty(window.navigator, 'languages', { value: ['vi-VN', 'vi'], configurable: true });
  });
  it('T3 a new priority with the same response changes only the highlighted row and the priority line', () => {
    const res = response();
    const view = card(res, 'cc1', 'income');
    const rows = () =>
      [...document.querySelectorAll('[data-testid^="card-cc1-row-"]')].map((r) => ({
        hook: r.getAttribute('data-testid'),
        hl: r.getAttribute('data-highlighted'),
        text: (r.textContent ?? '').replace(line('cc1')?.textContent ?? '', '').replace(vi.farmer.yourPriority, ''),
      }));
    const before = rows();
    const lineBefore = line('cc1')?.textContent;
    view.rerender('land');
    const after = rows();
    expect(after.map((r) => r.hook)).toEqual(before.map((r) => r.hook));
    expect(after.map((r) => r.text)).toEqual(before.map((r) => r.text));
    expect(after.filter((r) => r.hl).map((r) => r.hook)).toEqual(['card-cc1-row-land']);
    expect(before.filter((r) => r.hl).map((r) => r.hook)).toEqual(['card-cc1-row-money']);
    expect(line('cc1')?.textContent).not.toEqual(lineBefore);
  });
});
