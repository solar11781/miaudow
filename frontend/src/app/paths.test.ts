// D-174: every page also has an English path that opens the same page in English; the Vietnamese paths stay the main
// ones, and the answers after "?" in the fragment stay exactly as they are.
import { describe, expect, it } from 'vitest';
import { isEnglishPath, localTo, pathFor } from './paths';

const MAP: [string, string][] = [
  ['/', '/home'],
  ['/nong-dan', '/farmer'],
  ['/nong-dan/ruong', '/farmer/field'],
  ['/nong-dan/nam', '/farmer/years'],
  ['/nong-dan/uu-tien', '/farmer/priority'],
  ['/nong-dan/phuong-an', '/farmer/plans'],
  ['/can-bo', '/officer'],
  ['/khoa-hoc', '/science'],
  ['/phuong-phap', '/method'],
  ['/dai-quan-sat', '/observatory'],
  ['/bang-chung', '/evidence'],
  ['/tro-ly', '/assistant'],
  ['/dang-nhap', '/sign-in'],
  ['/da-luu', '/saved'],
];

describe('English paths', () => {
  it.each(MAP)('%s is %s in English and back', (vi, en) => {
    expect(pathFor(vi, 'en')).toBe(en);
    expect(pathFor(en, 'vi')).toBe(vi);
    // already in the asked language: unchanged
    expect(pathFor(en, 'en')).toBe(en);
    expect(pathFor(vi, 'vi')).toBe(vi);
    expect(isEnglishPath(en)).toBe(true);
    expect(isEnglishPath(vi)).toBe(false);
  });

  it('keeps the answers in the search part exactly', () => {
    const search = '?ruong=canal_end&nam=2010,2020&uutien=income';
    expect(localTo(`/nong-dan/phuong-an${search}`, 'en')).toBe(`/farmer/plans${search}`);
    expect(localTo({ pathname: '/nong-dan/nam', search }, 'en')).toEqual({ pathname: '/farmer/years', search });
    expect(localTo({ pathname: '/farmer/years', search }, 'vi')).toEqual({ pathname: '/nong-dan/nam', search });
    expect(localTo('/dang-nhap?ve=%2Fda-luu', 'en')).toBe('/sign-in?ve=%2Fda-luu');
  });

  it('leaves a path it does not know as it is', () => {
    expect(pathFor('/khong-co', 'en')).toBe('/khong-co');
    expect(localTo({ search: '?the=cc1' }, 'en')).toEqual({ search: '?the=cc1' });
  });
});
