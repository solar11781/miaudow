// D-165: the winter weather result is "narrow" and "fragile" wherever it appears, in the method report's words.
import { afterEach, describe, expect, it, vi as mock } from 'vitest';
import { cleanup, render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { SettingsProvider } from '../../app/settings';
import { ProvenanceProvider } from '../provenance/ProvenanceProvider';
import { api, validateMethod } from '../../api';
import method from '../../../snapshot/method.json';
import { MethodPage } from './MethodPage';
import { vi } from '../../i18n/vi';

function renderPage() {
  mock.spyOn(api, 'method').mockResolvedValue(validateMethod(method));
  render(
    <MemoryRouter>
      <SettingsProvider>
        <ProvenanceProvider>
          <MethodPage />
        </ProvenanceProvider>
      </SettingsProvider>
    </MemoryRouter>,
  );
}

describe('method page', () => {
  afterEach(() => {
    cleanup();
    mock.restoreAllMocks();
  });
  it('qualifies the winter weather claim as narrow and fragile', async () => {
    renderPage();
    const claim = await screen.findByText((_, el) => el?.textContent?.startsWith(vi.method.weatherClaim) ?? false, {
      selector: 'p',
    });
    expect(claim.textContent).toContain(vi.common.winterFragile);
  });
  // D-63 and UI-UX-SPEC section 11b item 5: the PICSA sentence, its source R-U19 one tap away
  it('shows the PICSA sentence with the PICSA field manual as its source', async () => {
    renderPage();
    const line = await screen.findByText(vi.method.picsa);
    await userEvent.click(within(line.closest('li') as HTMLElement).getByRole('button'));
    expect(document.querySelector('dialog[open]')?.textContent).toContain('PICSA Field Manual');
  });
});
