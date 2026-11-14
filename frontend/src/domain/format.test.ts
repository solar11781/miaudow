// The API sends Value strings in English notation (UI-UX-SPEC section 11: the backend rounds, the frontend shows the
// value as given); on screen Vietnamese uses a dot for thousands and a comma for decimals (review 2026-11-14).
import { describe, expect, it } from 'vitest';
import { displayUnit, displayValue } from './format';

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
});
