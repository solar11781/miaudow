import { describe, expect, it } from 'vitest';
import { en } from './en';
import { vi } from './vi';
import method from '../../snapshot/method.json';
import enSource from './en.ts?raw';

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
  // D-165: wherever the winter weather result appears, it says "narrow" and "fragile" in the method report's words
  // (src/fieldshift/ml/reports.py winter_claim_report, the E-018 report of the method response)
  it('words the winter result as the method report title', () => {
    const report = method.reports.find((r) => r.id === 'E-018');
    expect(vi.common.winterFragile).toBe(report?.title.vi);
    expect(en.common.winterFragile).toBe(report?.title.en);
  });
  // CLAUDE.md: money is the trial's, never the farmer's; a reference is not a forecast (final audit, 2026-11-15)
  it('qualify every profit summary with the trial and never call the baseline a forecast', () => {
    const vis = strings(vi);
    const ens = strings(en);
    for (const s of ['Tiền lãi cả năm trong thử nghiệm', 'Lãi cả năm trong thử nghiệm, ba vụ cộng lại'])
      expect(vis).toContain(s);
    for (const s of ['Profit over the year in the trial', 'Yearly profit in the trial, three seasons added'])
      expect(ens).toContain(s);
    expect(vis.filter((s) => /tiền lãi, nước/.test(s))).toEqual([]);
    expect(ens.filter((s) => / profit, (water|soil)/.test(s))).toEqual([]);
    expect(vis.filter((s) => /dự báo trung bình/.test(s))).toEqual([]);
    expect(ens.filter((s) => /climatology forecast/.test(s))).toEqual([]);
  });
  it('tell the user that the typed question goes to Anthropic when Claude is on (final audit 2026-11-15)', () => {
    expect(vi.copilot.claudeOn).toMatch(/Anthropic/);
    expect(en.copilot.claudeOn).toMatch(/Anthropic/);
  });
  it('say the copilot model only picks passages, shown word for word, and never words the answer (D-172)', () => {
    expect(en.copilot.claudeOn).toMatch(/word for word/);
    expect(vi.copilot.claudeOn).toMatch(/nguyên văn/);
    for (const s of [en.copilot.claudeOn, vi.copilot.claudeOn]) expect(s).not.toMatch(/words the answer|diễn đạt/);
  });
  it('never offer the climate ML section the D-169 audit hid (closest years, unusual years)', () => {
    for (const core of [...en.home.cores, ...vi.home.cores]) {
      expect(Object.values(core).join(' ')).not.toMatch(/alike|unusual|similar|giống nhau|bất thường/i);
    }
  });
  it('describe the copilot core as extractive: picked passages shown word for word with sources (D-177)', () => {
    const [enCore, viCore] = [en.home.cores[3], vi.home.cores[3]];
    expect(Object.values(enCore ?? {}).join(' ')).toMatch(/word for word/);
    expect(Object.values(viCore ?? {}).join(' ')).toMatch(/nguyên văn/);
    for (const text of [enCore, viCore].map((c) => Object.values(c ?? {}).join(' '))) {
      expect(text).not.toMatch(
        /checks every number|short answer|answer engine|kiểm từng con số|câu trả lời ngắn|bộ trả lời/i,
      );
    }
  });
});

// D-186: English text writes "Nghe An" and "Vietnam"; titles, names and quotes stay verbatim (the journal "Nghệ An S&T")
describe('place names in English', () => {
  it('use Nghe An and Vietnam outside verbatim titles', () => {
    const lines = enSource.split(/\r?\n/).filter((l) => /Nghệ An|Viet Nam|Việt Nam/.test(l) && !l.includes('S&T'));
    expect(lines).toEqual([]);
  });
});
