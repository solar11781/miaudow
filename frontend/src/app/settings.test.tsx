import { act, render } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { SettingsProvider } from './settings';

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
