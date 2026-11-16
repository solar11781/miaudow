// The API sends Value strings in English notation (UI-UX-SPEC section 11: the backend rounds, the frontend shows the
// value as given); on screen Vietnamese uses a dot for thousands and a comma for decimals (review 2026-11-14).
import { describe, expect, it } from 'vitest';
import { displayMeasure, displayUnit, displayValue, lowerFirst, upperFirst, withUnit } from './format';

describe('value display', () => {
  it('groups thousands with a dot and decimals with a comma in Vietnamese', () => {
    expect(displayValue('30,799', 'vi')).toBe('30.799');
    expect(displayValue('6,500-7,500', 'vi')).toBe('6.500-7.500');
    expect(displayValue('0.42', 'vi')).toBe('0,42');
    expect(displayValue('1,234.5', 'vi')).toBe('1.234,5');
    expect(displayValue('-3', 'vi')).toBe('-3');
  });
  it('keeps the English notation in English', () => {
    expect(displayValue('30,799', 'en')).toBe('30,799');
    expect(displayValue('0.42', 'en')).toBe('0.42');
  });
  it('writes cubic metres as m³', () => {
    expect(displayUnit('m3/ha')).toBe('m³/ha');
    expect(displayUnit('nghìn đồng/ha')).toBe('nghìn đồng/ha');
    expect(displayUnit('mm')).toBe('mm');
  });
  // D-170: m³ and m² also inside API text, e.g. a source's limitation about a 1000 m2 plot
  it('writes square metres as m² in units and in text', () => {
    expect(displayUnit('m2')).toBe('m²');
    expect(displayUnit('one 1000 m2 plot per crop; 6,500 m3/ha')).toBe('one 1000 m² plot per crop; 6,500 m³/ha');
    expect(displayUnit('R-M2 and mm2x stay')).toBe('R-M2 and mm2x stay');
  });
  // rules/rotations.yaml writes the P-02 plot as "1000 m2"; the text files write "1.000 m²" and "1,000 m²" (D-170)
  it('writes the thousands mark of the language in a size before m² or m³, and nowhere else', () => {
    expect(displayMeasure('Mỗi cây một ô 1000 m2, không lặp lại', 'vi')).toBe('Mỗi cây một ô 1.000 m², không lặp lại');
    expect(displayMeasure('One unreplicated 1000 m2 plot per crop', 'en')).toBe(
      'One unreplicated 1,000 m² plot per crop',
    );
    expect(displayMeasure('June 2020 to June 2021 (p. 45); 6,500 m3/ha; 250 m2', 'en')).toBe(
      'June 2020 to June 2021 (p. 45); 6,500 m³/ha; 250 m²',
    );
  });
  // the app writes percent with no space ("100%" in the soil label, UI-UX-SPEC section 9); the API sends "%" as a unit
  it('joins a percent sign to its number and keeps the space before any other unit', () => {
    expect(withUnit('55', '%')).toBe('55%');
    expect(withUnit('2.000', 'm³/ha')).toBe('2.000 m³/ha');
    expect(withUnit('3', '')).toBe('3');
  });
});

describe('first letter case', () => {
  it('changes only the first letter, Vietnamese letters included', () => {
    expect(lowerFirst('Lúa vụ Đông Xuân')).toBe('lúa vụ Đông Xuân');
    expect(lowerFirst('Spring rice')).toBe('spring rice');
    expect(upperFirst('đất lúa')).toBe('Đất lúa');
    expect(upperFirst('')).toBe('');
  });
});
