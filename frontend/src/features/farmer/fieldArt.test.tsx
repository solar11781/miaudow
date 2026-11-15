// R-H15 and hand-off item 9: the field-step pictures are AI-generated (lamgiang/assets/field-conditions/manifest.json,
// "AI-generated photorealistic concept illustration"), so they are listed in media.json as illustrations and drawn
// by the one image component, like the other AI pictures.
import type { ReactElement } from 'react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { cleanup, render } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { SettingsProvider } from '../../app/settings';
import { MEDIA } from '../../data/media';
import { FarmerLayout } from './FarmerLayout';
import { LandStep } from './LandStep';
import { StartStep } from './StartStep';
import { en } from '../../i18n/en';
import { vi as viText } from '../../i18n/vi';

const FIELD = [
  'high-field-hard-to-water',
  'field-at-end-of-canal',
  'field-often-short-of-water',
  'water-under-control',
  'ask-extension-officer',
];

function renderStep(path: string, element: ReactElement) {
  return render(
    <SettingsProvider>
      <MemoryRouter initialEntries={[path]}>
        <Routes>
          <Route element={<FarmerLayout />}>
            <Route path={path} element={element} />
          </Route>
        </Routes>
      </MemoryRouter>
    </SettingsProvider>,
  );
}

const fieldPictures = (container: HTMLElement) =>
  [...container.querySelectorAll('img')]
    .map((img) => img.getAttribute('src') ?? '')
    .filter((src) => src.includes('/field/'));

describe('field-step illustrations', () => {
  afterEach(() => {
    cleanup();
    vi.unstubAllGlobals();
  });
  vi.stubGlobal(
    'fetch',
    vi.fn(async () => new Response('{}', { status: 503 })),
  );

  it.each(FIELD)('lists %s in media.json as an AI illustration', (slug) => {
    expect(MEDIA[slug]?.kind).toBe('illustration');
  });

  it('draws the five field cards from media.json', () => {
    const { container } = renderStep('/nong-dan/ruong', <LandStep />);
    const listed = FIELD.map((slug) => MEDIA[slug]?.sources[0]?.webp);
    expect(fieldPictures(container)).toEqual(listed);
  });

  it('draws the four start-step pictures from media.json', () => {
    const { container } = renderStep('/nong-dan', <StartStep />);
    expect(fieldPictures(container)).toEqual(FIELD.slice(1).map((slug) => MEDIA[slug]?.sources[0]?.webp));
  });

  it('says under the field cards that the pictures are made with AI', () => {
    expect(viText.farmer.artNote).toMatch(/\bAI\b/);
    expect(en.farmer.artNote).toMatch(/\bAI\b/);
  });
});
