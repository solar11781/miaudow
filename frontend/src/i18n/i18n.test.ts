import { describe, expect, it } from 'vitest';
import { en } from './en';
import { vi } from './vi';

type Node = unknown;

function shape(node: Node, path = ''): string[] {
  if (typeof node === 'function') return [`${path}()/${node.length}`];
  if (Array.isArray(node)) return [`${path}[${node.length}]`, ...node.flatMap((v, i) => shape(v, `${path}[${i}]`))];
  if (node && typeof node === 'object')
    return Object.entries(node).flatMap(([k, v]) => shape(v, path ? `${path}.${k}` : k));
  return [path];
}

function strings(node: Node): string[] {
  if (typeof node === 'string') return [node];
  if (Array.isArray(node)) return node.flatMap(strings);
  if (node && typeof node === 'object') return Object.values(node).flatMap(strings);
  return [];
}

describe('translations', () => {
  it('have exactly the same keys, list lengths and function arities', () => {
    expect(shape(en).sort()).toEqual(shape(vi).sort());
  });
  it('have no empty strings', () => {
    for (const s of [...strings(vi), ...strings(en)]) expect(s.trim().length).toBeGreaterThan(0);
  });
  it('keep Vietnamese diacritics in the Vietnamese text', () => {
    expect(vi.common.notForecast).toBe('Năm đã qua, không phải dự báo');
    expect(strings(vi).join(' ')).toMatch(/[ăâđêôơưạảấầẩẫậắằẳẵặẹẻẽếềểễệỉịọỏốồổỗộớờởỡợụủứừửữựỳỵỷỹ]/);
  });
  // CLAUDE.md: no profit claim for the farmer's own field; UI-UX-SPEC section 9 money row: P-02 Table 13 "Lãi thuần",
  // Tables 4, 8, 12 "Tổng chi"
  it('label the money as the trial figures', () => {
    expect(vi.farmer.profit).toContain('Lãi thuần');
    expect(vi.farmer.cost).toContain('Tổng chi');
    for (const label of [vi.farmer.rows.money, vi.farmer.profit, vi.farmer.cost]) expect(label).toContain('thử nghiệm');
    for (const label of [en.farmer.rows.money, en.farmer.profit, en.farmer.cost]) expect(label).toContain('trial');
  });
});
