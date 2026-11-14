import { describe, expect, it } from 'vitest';
import { answer, type Fmt } from './answer';
import { normalize } from './normalize';
import { isStrong, search } from './retrieve';
import { yearShare } from '../../domain/hazards';
import { PLANS } from '../../domain/plans';

const f: Fmt = {
  pct: (v) => `${Math.round(v * 100)}%`,
  signedPct: (v) => `${v > 0 ? '+' : ''}${(v * 100).toFixed(1)}%`,
  n: (v, d = 0) => v.toFixed(d),
};
const text = { noEvidence: 'NO_EVIDENCE', noRanking: 'NO_RANKING' };
const ask = (q: string, lang: 'vi' | 'en' = 'vi') => answer(q, lang, f, text);

describe('normalisation', () => {
  it('strips Vietnamese diacritics and đ', () => {
    expect(normalize('Đồng LÚA, hạn hán!')).toBe('dong lua han han');
  });
});

describe('retrieval', () => {
  it.each([
    ['Dữ liệu NASA là gì?', 'nasa-power'],
    ['du lieu nasa la gi', 'nasa-power'],
    ['Ngưỡng rủi ro lấy từ đâu?', 'qd18'],
    ['lúa hè thu có lãi không', 'p03-summer'],
    ['Lúa cần bao nhiêu nước?', 'water-units'],
    ['cây họ đậu có tốt cho đất không', 'legume'],
    ['What is the NASA data?', 'nasa-power'],
  ])('finds the right passage for “%s”', (q, id) => {
    const hits = search(q);
    expect(hits[0]?.passage.id).toBe(id);
    expect(hits[0] && isStrong(hits[0])).toBe(true);
  });
});

describe('answers', () => {
  it('looks up a year with the exact computed shares', () => {
    const a = ask('Năm 2010 có hạn không?');
    expect(a.type).toBe('year');
    const drought = a.lines.find((l) => l.ref?.label.startsWith('Hạn (phần mưa)'));
    expect(drought?.ref?.value).toBe(f.pct(yearShare('drought_rain_any2', 2010)));
  });
  it('abstains for a year outside the data', () => {
    expect(ask('năm 1980 thế nào').type).toBe('abstain');
  });
  it('refuses to rank plans and still shows each one', () => {
    const a = ask('Nên trồng gì cho ruộng nhà tôi?');
    expect(a.type).toBe('no-ranking');
    expect(a.lines[0]?.text).toBe('NO_RANKING');
    expect(a.lines.filter((l) => l.ref)).toHaveLength(PLANS.length);
  });
  it('answers a crop question from the trial table, without accents too', () => {
    const a = ask('trong lac lai bao nhieu');
    expect(a.type).toBe('crop');
    expect(a.lines.some((l) => l.ref?.value.startsWith('26.0'))).toBe(true);
  });
  it('says it has no evidence for unrelated questions', () => {
    for (const q of ['giá vé máy bay đi Đà Nẵng', 'bóng đá tối nay', 'công thức nấu phở', 'tỉ số trận đấu', '']) {
      expect(ask(q).type, q).toBe('abstain');
    }
  });
  it('answers a forecast question by saying the app does not forecast', () => {
    for (const q of ['thời tiết Hà Nội ngày mai', 'mùa tới có hạn không', 'will it be dry next season']) {
      const a = ask(q);
      expect(a.evidence[0]?.passage.id, q).toBe('no-forecast');
    }
  });
  it('only shows numbers that exist in the data', () => {
    const a = ask('Năm 2015 thế nào?', 'en');
    for (const l of a.lines) if (l.ref?.sourceId === 'nasa-power') expect(l.ref.value).toMatch(/^\d{1,3}%$/);
  });
});
