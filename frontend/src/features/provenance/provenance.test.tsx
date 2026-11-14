import { describe, expect, it } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { SettingsProvider } from '../../app/settings';
import { ProvenanceProvider } from './ProvenanceProvider';
import { SourceValue } from './SourceValue';

describe('source seal', () => {
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
});
