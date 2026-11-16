// D-198 (member A, 2026-11-17): the trial site's commune was merged into xã Đô Lương by Resolution 1678/NQ-UBTVQH15
// (16 June 2025, Article 1, item 20). The app's own words say so; facts about a source (its place as published,
// titles, quotes) stay as the source wrote them.
import { describe, expect, it } from 'vitest';
import { en } from './en';
import { vi } from './vi';
import { PASSAGES } from '../features/ai/knowledge';
import { MISSIONS } from '../features/earth/missions';
import { SOURCES } from '../domain/sources';

/** Every text of a message tree; a text function is read with placeholder arguments. */
function texts(node: unknown): string[] {
  if (typeof node === 'string') return [node];
  if (typeof node === 'function') return texts((node as (...a: string[]) => unknown)('x', 'x', 'x', 'x'));
  if (Array.isArray(node)) return node.flatMap(texts);
  if (node && typeof node === 'object') return Object.values(node).flatMap(texts);
  return [];
}

const ownWords = (lang: 'vi' | 'en') => [
  ...texts(lang === 'vi' ? vi : en),
  ...PASSAGES.flatMap((p) => [p.title[lang], p.text[lang]]),
  ...MISSIONS.map((m) => m.statusNote[lang]),
  // a data source's fields describe our use of it; a study's place is the study's own, and the resolution's list of
  // merged communes is the law's own wording
  ...Object.values(SOURCES)
    .filter((s) => s.kind !== 'study' && s.id !== 'nq1678')
    .flatMap((s) => [s.where[lang], s.method[lang], s.caveat[lang]]),
];

describe('place names after 2025 (D-198)', () => {
  it('the officer page gives the trial site with its current commune and its source', () => {
    expect(vi.officer.scope[0]).toEqual({
      label: 'Nơi thử nghiệm',
      value: 'Xã Lưu Sơn (cũ), huyện Đô Lương (cũ), nay thuộc xã Đô Lương, Nghệ An',
      source: 'nq1678',
    });
    expect(en.officer.scope[0]).toEqual({
      label: 'Trial site',
      value: 'Former Luu Son commune, former Do Luong district, now part of Do Luong commune, Nghe An',
      source: 'nq1678',
    });
    expect(SOURCES.nq1678.registerId).toBe('R-V10');
  });

  it('the app never names Lưu Sơn in its own words without saying it is the former commune', () => {
    expect(ownWords('vi').filter((s) => /Lưu Sơn(?! \(cũ\))/.test(s))).toEqual([]);
    expect(ownWords('en').filter((s) => /(?<![Ff]ormer )Luu Son/.test(s))).toEqual([]);
  });
});
