// Visual audit 2026-11-16: the data room page mixed number notations in Vietnamese ("19.0°N 105.625°E", "49.9") and
// showed the internal cell key "19.0_105.0" in a source label. Vietnamese uses a decimal comma on the whole page,
// English a decimal point, and a cell is named by its centre.
import { afterEach, beforeAll, describe, expect, it } from 'vitest';
import { cleanup, render, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { SettingsProvider } from '../../app/settings';
import { ProvenanceProvider } from '../provenance/ProvenanceProvider';
import { SciencePage } from './SciencePage';
import observatorySource from './Observatory3D.tsx?raw';

async function page(languages: string[]) {
  Object.defineProperty(window.navigator, 'languages', { value: languages, configurable: true });
  render(
    <SettingsProvider>
      <ProvenanceProvider>
        <MemoryRouter initialEntries={['/khoa-hoc?nam=2010']}>
          <SciencePage />
        </MemoryRouter>
      </ProvenanceProvider>
    </SettingsProvider>,
  );
  await waitFor(() => expect(document.querySelector('button[aria-pressed]')).not.toBeNull());
  return document.body.textContent ?? '';
}

describe('data room number notation', () => {
  // the map arrives in its own chunk, with three.js: load it once before the page is drawn
  beforeAll(() => import('./Observatory3D'), 30_000);
  afterEach(() => {
    cleanup();
    Object.defineProperty(window.navigator, 'languages', { value: ['vi-VN', 'vi'], configurable: true });
  });

  it('writes every cell centre with a decimal comma in Vietnamese', async () => {
    const text = await page(['vi-VN', 'vi']);
    expect(text).toContain('19,0°B 105,625°Đ');
    expect(text).not.toMatch(/\d\.\d+°/);
    expect(text).not.toMatch(/°[NE]\b/);
    expect([...document.querySelectorAll('option')].map((o) => o.textContent)).toContain('19,0°B 105,000°Đ');
    expect(document.querySelector('button[aria-pressed]')?.getAttribute('aria-label')).not.toMatch(/\d\.\d/);
  });

  it('keeps the decimal point in English', async () => {
    const text = await page(['en-GB', 'en']);
    expect(text).toContain('19.0°N 105.625°E');
    expect(text).not.toMatch(/\d,\d+°/);
    expect([...document.querySelectorAll('option')].map((o) => o.textContent)).toContain('19.0°N 105.000°E');
  });

  // data/canonical/climate.json: NASA POWER cell 19.0_105.0, January 2010, 49.9 mm
  it('writes the monthly rain of the two sources in the reading language', async () => {
    const rain = () => [...document.querySelectorAll('table')].find((t) => t.textContent?.includes('CHIRPS v3'));
    await page(['vi-VN', 'vi']);
    expect(rain()?.textContent).toContain('49,9');
    expect(rain()?.textContent).not.toMatch(/\d\.\d/);
    cleanup();
    await page(['en-GB', 'en']);
    expect(rain()?.textContent).toContain('49.9');
  });

  it('names the cell in the source label of the two rain totals instead of its internal key', async () => {
    const text = await page(['vi-VN', 'vi']);
    expect(text).not.toContain('19.0_105.0');
    expect(text).toContain('NASA POWER · 2010 · ô lưới 19,0°B 105,000°Đ');
    cleanup();
    expect(await page(['en-GB', 'en'])).toContain('NASA POWER · 2010 · grid cell 19.0°N 105.000°E');
  });

  // the 3D map needs WebGL, which the test browser does not have, so this reads the source
  it('takes the word before the tallest column value from the text files', () => {
    expect(observatorySource).not.toMatch(/· max \{/);
    expect(observatorySource).toContain('{t.science.max} {f.n(magMax)}');
  });
});
