import { afterEach, describe, expect, it } from 'vitest';
import { cleanup, render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { SettingsProvider } from '../../app/settings';
import { ProvenanceProvider } from './ProvenanceProvider';
import { SourceValue } from './SourceValue';

describe('source seal', () => {
  afterEach(cleanup);
  it('opens the provenance sheet with the source, kind and caveat', async () => {
    render(
      <SettingsProvider>
        <ProvenanceProvider>
          <SourceValue sourceId="p02" kind="study" value="25,98 triệu đ/ha" label="Lãi Lạc L20" />
        </ProvenanceProvider>
      </SettingsProvider>,
    );
    await userEvent.click(screen.getByRole('button', { name: /Lãi Lạc L20: 25,98 triệu đ\/ha/ }));
    const dialog = document.querySelector('dialog[open]');
    expect(dialog).not.toBeNull();
    expect(dialog?.textContent).toContain('Kết quả thử nghiệm một số cây trồng');
    expect(dialog?.textContent).toContain('Kết quả nghiên cứu');
    expect(dialog?.textContent).toContain('Có thể không đúng khi');
  });
  it.each([
    ['chirps-v3', 'R-D05'],
    ['modis-ndvi', 'R-N11'],
    ['nasa-power', 'R-N01'],
    ['sentinel2', 'R-D06'], // REFERENCES R-D06: the observatory's Copernicus Sentinel-2 L2A images
  ] as const)('shows the register id of %s (%s) in its sheet', async (id, registerId) => {
    render(
      <SettingsProvider>
        <ProvenanceProvider>
          <SourceValue sourceId={id} kind="data" value="1 mm" label="Giá trị" />
        </ProvenanceProvider>
      </SettingsProvider>,
    );
    await userEvent.click(screen.getByRole('button', { name: /Giá trị: 1 mm/ }));
    expect(document.querySelector('dialog[open]')?.textContent).toContain(registerId);
  });
});

// D-170: the source sheet writes m² and m³ in the API's own text
describe('api source sheet', () => {
  afterEach(cleanup);
  it('writes square metres with the superscript', async () => {
    const text = { vi: 'một ô 1000 m2 cho mỗi cây', en: 'one 1000 m2 plot per crop' };
    const facts = {
      id: 'R-P02',
      citation: text,
      study_type: text,
      place_years: text,
      read_status: null,
      full_text_read: null,
      limitations: [text],
      url: null,
      nso_credit: false,
    };
    render(
      <SettingsProvider>
        <ProvenanceProvider>
          <SourceValue facts={[facts]} value="5" label="ô thử" />
        </ProvenanceProvider>
      </SettingsProvider>,
    );
    await userEvent.click(screen.getByRole('button', { name: /ô thử/ }));
    const sheet = document.querySelector('[data-testid="source-sheet"]')?.textContent ?? '';
    expect(sheet).toContain('1000 m²');
    expect(sheet).not.toContain('m2');
  });
});
