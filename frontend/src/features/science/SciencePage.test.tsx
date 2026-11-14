// D-165: the winter weather result is "narrow" and "fragile" wherever it appears, in the method report's words.
import { afterEach, describe, expect, it } from 'vitest';
import { cleanup, render } from '@testing-library/react';
import { SettingsProvider } from '../../app/settings';
import { ProvenanceProvider } from '../provenance/ProvenanceProvider';
import { RiceSection } from './SciencePage';
import { vi } from '../../i18n/vi';

describe('science rice chart', () => {
  afterEach(cleanup);
  it('says the winter result is narrow and fragile where the winter model estimates are shown', () => {
    render(
      <SettingsProvider>
        <ProvenanceProvider>
          <RiceSection />
        </ProvenanceProvider>
      </SettingsProvider>,
    );
    const section = document.querySelector('[aria-labelledby="rice-title"]');
    expect(section?.textContent).toContain(vi.science.predicted);
    expect(section?.textContent).toContain(vi.common.winterFragile);
  });
});
