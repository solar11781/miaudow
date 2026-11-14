// D-165: the winter weather result is "narrow" and "fragile" wherever it appears, in the method report's words.
import { afterEach, describe, expect, it, vi as mock } from 'vitest';
import { cleanup, render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { SettingsProvider } from '../../app/settings';
import { ProvenanceProvider } from '../provenance/ProvenanceProvider';
import { api, validateMethod } from '../../api';
import method from '../../../snapshot/method.json';
import { MethodPage } from './MethodPage';
import { vi } from '../../i18n/vi';

describe('method page', () => {
  afterEach(() => {
    cleanup();
    mock.restoreAllMocks();
  });
  it('qualifies the winter weather claim as narrow and fragile', async () => {
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
    const claim = await screen.findByText((_, el) => el?.textContent?.startsWith(vi.method.weatherClaim) ?? false, {
      selector: 'p',
    });
    expect(claim.textContent).toContain(vi.common.winterFragile);
  });
});
