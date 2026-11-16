// Visual audit 2026-11-16: a grid cell has one name on every screen, written in the reading language's number
// notation (Vietnamese: decimal comma, Bắc and Đông; English: decimal point, N and E). The cell centres are the
// NASA POWER grid's own (data/canonical/geo.json): 19.0, 105.0 and 19.0, 105.625.
import { afterEach, describe, expect, it } from 'vitest';
import { cleanup, renderHook } from '@testing-library/react';
import { SettingsProvider } from '../app/settings';
import { useCellName } from './useCellName';

describe('grid cell name', () => {
  afterEach(() => {
    cleanup();
    Object.defineProperty(window.navigator, 'languages', { value: ['vi-VN', 'vi'], configurable: true });
  });
  it.each([
    [['vi-VN', 'vi'], '19.0_105.625', '19,0°B 105,625°Đ'],
    [['vi-VN', 'vi'], '19.0_105.0', '19,0°B 105,000°Đ'],
    [['en-GB', 'en'], '19.0_105.625', '19.0°N 105.625°E'],
    [['en-GB', 'en'], '19.0_105.0', '19.0°N 105.000°E'],
  ])('writes the cell centre in the reading language (%s, %s)', (languages, id, name) => {
    Object.defineProperty(window.navigator, 'languages', { value: languages, configurable: true });
    const { result } = renderHook(() => useCellName(), { wrapper: SettingsProvider });
    expect(result.current(id)).toBe(name);
  });
});
