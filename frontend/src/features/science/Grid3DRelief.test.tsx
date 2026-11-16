// D-138, UI-UX-SPEC section 12: the optional NASA SRTM shaded relief under the flat map. Off by default, loads only
// when switched on, always says "height only" while it is on, and names its data and its shading method (H5).
import { afterEach, describe, expect, it } from 'vitest';
import { cleanup, render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { SettingsProvider } from '../../app/settings';
import { ProvenanceProvider } from '../provenance/ProvenanceProvider';
import { vi } from '../../i18n/vi';
import { en } from '../../i18n/en';
import { SOURCES } from '../../domain/sources';
import { Grid3D } from './Grid3D';

function flatMap() {
  render(
    <SettingsProvider>
      <ProvenanceProvider>
        <Grid3D rule="heat" year={2010} selected="" onSelect={() => undefined} forceFlat />
      </ProvenanceProvider>
    </SettingsProvider>,
  );
}

const relief = () => document.querySelector('image[href*="nghe-an-relief"]');

describe('terrain layer of the flat map', () => {
  afterEach(cleanup);
  it('is off at first: no picture in the page and a pressable button that says so', () => {
    flatMap();
    const button = screen.getByRole('button', { name: vi.science.reliefToggle });
    expect(button.getAttribute('aria-pressed')).toBe('false');
    expect(relief()).toBeNull();
    expect(document.body.textContent).not.toContain(vi.science.reliefNote);
  });
  it('draws the picture and the height-only note when switched on, and removes both when switched off', async () => {
    flatMap();
    const button = screen.getByRole('button', { name: vi.science.reliefToggle });
    await userEvent.click(button);
    expect(button.getAttribute('aria-pressed')).toBe('true');
    expect(relief()).not.toBeNull();
    expect(document.body.textContent).toContain(vi.science.reliefNote);
    await userEvent.click(button);
    expect(relief()).toBeNull();
    expect(document.body.textContent).not.toContain(vi.science.reliefNote);
  });
  it('opens a source sheet naming NASA SRTM and the Horn (1981) shading', async () => {
    flatMap();
    await userEvent.click(screen.getByRole('button', { name: vi.science.reliefToggle }));
    await userEvent.click(screen.getByRole('button', { name: /NASA SRTM, Địa hình Nghệ An/ }));
    const sheet = document.querySelector('dialog[open]')?.textContent ?? '';
    expect(sheet).toContain('R-N12');
    expect(sheet).toContain('SRTM');
    expect(sheet).toContain('Horn');
    expect(sheet).toContain('315');
  });
  it('has the words of the spec in both languages', () => {
    expect(vi.science.reliefToggle).toBe('Địa hình (NASA SRTM)');
    expect(vi.science.reliefNote).toBe('Chỉ là độ cao. Không cho biết nước tới được đâu.');
    expect(en.science.reliefToggle).toBe('Terrain (NASA SRTM)');
    expect(en.science.reliefNote).toBe('Height only. It says nothing about where water reaches.');
  });
  it('registers the dataset with its register id and licence', () => {
    expect(SOURCES['nasa-srtm'].registerId).toBe('R-N12');
    expect(SOURCES['nasa-srtm'].url).toBe('https://doi.org/10.5067/MEaSUREs/SRTM/SRTMGL3.003');
    expect(SOURCES['nasa-srtm'].licence?.en).toContain('NASA');
  });
});
