// D-174: in English every link opens the English path of its page.
import { afterEach, describe, expect, it } from 'vitest';
import { cleanup, render } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { SettingsProvider } from '../app/settings';
import { CoreTag } from './CoreTag';

describe('CoreTag', () => {
  afterEach(() => {
    cleanup();
    Object.defineProperty(window.navigator, 'languages', { value: ['vi-VN', 'vi'], configurable: true });
  });
  it.each([
    [['vi-VN', 'vi'], '/'],
    [['en-GB', 'en'], '/home'],
  ])('links to the home page of the reading language (%s)', (languages, home) => {
    Object.defineProperty(window.navigator, 'languages', { value: languages, configurable: true });
    const { container } = render(
      <SettingsProvider>
        <MemoryRouter>
          <CoreTag core="evidence" />
        </MemoryRouter>
      </SettingsProvider>,
    );
    expect(container.querySelector('a')?.getAttribute('href')).toBe(home);
  });
});
