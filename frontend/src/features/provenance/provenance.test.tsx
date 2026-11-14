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
