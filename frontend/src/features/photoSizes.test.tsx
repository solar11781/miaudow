import { afterEach, describe, expect, it, vi } from 'vitest';
import { cleanup, render } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { SettingsProvider } from '../app/settings';
import { ProvenanceProvider } from './provenance/ProvenanceProvider';
import { FarmerLayout } from './farmer/FarmerLayout';
import { StartStep } from './farmer/StartStep';
import { HomePage } from './home/HomePage';

// A phone at 360 px shows these photos about 328 px wide, so at DPR 2 the 640w file is enough; 100vw or 92vw made
// phones load the 1280w file (performance audit, Slow 4G).
const widths = (container: HTMLElement) =>
  [...container.querySelectorAll('source[type="image/avif"]')].map((el) => el.getAttribute('sizes'));

describe('photo sizes', () => {
  afterEach(() => {
    cleanup();
    vi.unstubAllGlobals();
  });
  vi.stubGlobal(
    'fetch',
    vi.fn(async () => new Response('{}', { status: 503 })),
  );

  it('lets a phone load the 640w start photo', () => {
    const { container } = render(
      <SettingsProvider>
        <MemoryRouter initialEntries={['/start']}>
          <Routes>
            <Route element={<FarmerLayout />}>
              <Route path="/start" element={<StartStep />} />
            </Route>
          </Routes>
        </MemoryRouter>
      </SettingsProvider>,
    );
    expect(widths(container)).toEqual(['(max-width: 700px) 320px, 600px']);
  });

  it('lets a phone load the 640w home photos below the fold', () => {
    const { container } = render(
      <SettingsProvider>
        <ProvenanceProvider>
          <MemoryRouter>
            <HomePage />
          </MemoryRouter>
        </ProvenanceProvider>
      </SettingsProvider>,
    );
    const sizes = widths(container).filter((x): x is string => x !== null);
    expect(sizes.length).toBeGreaterThan(3);
    expect(sizes.filter((x) => x.includes('92vw'))).toEqual([]);
    // the redesigned home (hero, problem, verse, AI cores, steps, invitation): every photo keeps the phone rule
    expect(sizes.filter((x) => !x.startsWith('(max-width: 480px) 320px, '))).toEqual([]);
  });
});
