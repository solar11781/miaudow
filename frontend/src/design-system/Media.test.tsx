// Space Apps 2026 submission guide: AI-generated images are marked as made by AI; the label and the alt text say so.
import { afterEach, describe, expect, it } from 'vitest';
import { cleanup, render } from '@testing-library/react';
import { SettingsProvider } from '../app/settings';
import { MEDIA } from '../data/media';
import { Media } from './Media';

describe('Media label for AI illustrations', () => {
  afterEach(cleanup);
  it('says on the picture that AI made it', () => {
    const { container } = render(
      <SettingsProvider>
        <Media slug="d1-horizon" sizes="100vw" />
      </SettingsProvider>,
    );
    expect(container.textContent).toBe('Tranh do AI tạo, không phải ảnh thật');
    expect(container.querySelector('picture img')?.getAttribute('alt')).toMatch(/^Tranh do AI tạo: /);
  });
  it('starts every illustration alt text with the AI words in both languages', () => {
    const art = Object.values(MEDIA).filter((m) => m.kind === 'illustration');
    expect(art).toHaveLength(16);
    for (const m of art) {
      expect(m.alt.vi).toMatch(/^Tranh do AI tạo: /);
      expect(m.alt.en).toMatch(/^AI-generated illustration: /);
    }
  });
});
