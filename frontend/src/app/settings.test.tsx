import { act, render, renderHook } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { SettingsProvider, useFormat } from './settings';

/** A stand-in for the browser's colour-scheme setting that the test can flip, like a phone switching to light. */
function systemScheme(light: boolean) {
  const listeners = new Set<() => void>();
  const mq = {
    get matches() {
      return light;
    },
    addEventListener: (_: string, on: () => void) => listeners.add(on),
    removeEventListener: (_: string, on: () => void) => listeners.delete(on),
  };
  vi.spyOn(window, 'matchMedia').mockImplementation(
    (query: string) =>
      (query === '(prefers-color-scheme: light)'
        ? mq
        : { matches: false, addEventListener() {}, removeEventListener() {} }) as unknown as MediaQueryList,
  );
  return (next: boolean) => {
    light = next;
    listeners.forEach((on) => on());
  };
}

afterEach(() => {
  vi.restoreAllMocks();
});

// audit F10, D-187: the theme "Auto" stayed dark on a phone set to light mode
describe('theme Auto follows the system colour scheme', () => {
  it('uses the light theme when the phone is in light mode', () => {
    systemScheme(true);
    render(<SettingsProvider>{null}</SettingsProvider>);
    expect(document.documentElement.dataset.theme).toBe('light');
  });

  it('uses the dark theme when the phone is in dark mode, and follows a later switch', () => {
    const flip = systemScheme(false);
    render(<SettingsProvider>{null}</SettingsProvider>);
    expect(document.documentElement.dataset.theme).toBe('dark');
    act(() => flip(true));
    expect(document.documentElement.dataset.theme).toBe('light');
  });
});

// visual audit of the method page: a small negative value rounded to zero was printed as "-0,00"
describe('number formatting', () => {
  afterEach(() => {
    Object.defineProperty(window.navigator, 'languages', { value: ['vi-VN', 'vi'], configurable: true });
  });

  it.each([
    [['vi-VN', 'vi'], '0,00', '-0,01', '0'],
    [['en-GB', 'en'], '0.00', '-0.01', '0'],
  ])('prints a value that rounds to zero without a minus sign (%s)', (languages, zero, negative, whole) => {
    Object.defineProperty(window.navigator, 'languages', { value: languages, configurable: true });
    const { result } = renderHook(() => useFormat(), { wrapper: SettingsProvider });
    expect(result.current.n(-0.004, 2)).toBe(zero);
    expect(result.current.n(-0, 2)).toBe(zero);
    expect(result.current.n(-0.006, 2)).toBe(negative);
    expect(result.current.n(-0.4)).toBe(whole);
    expect(result.current.pct(-0.004)).toBe(`${whole}%`);
  });
});
