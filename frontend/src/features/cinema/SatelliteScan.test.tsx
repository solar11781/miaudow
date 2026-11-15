// H5: every displayed number has a source. The drawn orbits are illustrations, so the scene shows no coordinates.
import { afterEach, describe, expect, it } from 'vitest';
import { cleanup, render } from '@testing-library/react';
import { SettingsProvider } from '../../app/settings';
import { vi as viText } from '../../i18n/vi';
import { SatelliteScan } from './SatelliteScan';

describe('SatelliteScan', () => {
  afterEach(cleanup);
  it('shows no latitude or longitude', () => {
    const { container } = render(
      <SettingsProvider>
        <SatelliteScan labels={viText.earth.scan} />
      </SettingsProvider>,
    );
    expect(container.textContent).not.toMatch(/\d\s*°/);
  });
});
