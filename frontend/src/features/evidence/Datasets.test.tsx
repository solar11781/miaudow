// visual audit 2026-11-16: the data register showed long web addresses that broke inside narrow cells, and the plot
// size without the m² sign. Each address is a short link (the host as its text), the address itself the target.
import { afterEach, describe, expect, it } from 'vitest';
import { cleanup, render } from '@testing-library/react';
import { SettingsProvider } from '../../app/settings';
import { Datasets } from './Datasets';

function register(languages: string[]) {
  Object.defineProperty(window.navigator, 'languages', { value: languages, configurable: true });
  render(
    <SettingsProvider>
      <Datasets />
    </SettingsProvider>,
  );
  return document.body;
}

describe('data register', () => {
  afterEach(() => {
    cleanup();
    Object.defineProperty(window.navigator, 'languages', { value: ['vi-VN', 'vi'], configurable: true });
  });

  it.each([['vi-VN'], ['en-US']])('shows each web address as a short link to it (%s)', (language) => {
    const body = register([language]);
    expect(body.textContent).not.toMatch(/https?:|\.org\/|\.eu\//);
    const links = [...body.querySelectorAll('dd a')].map((a) => [a.textContent, a.getAttribute('href')]);
    // catalog.json licences: chirps_v3_monthly, modis_mod13q1_ndvi, sentinel2_l2a_do_luong_vi,
    // geoboundaries_vnm_adm2_do_luong
    expect(links).toEqual(
      expect.arrayContaining([
        ['creativecommons.org', 'https://creativecommons.org/licenses/by/4.0/'],
        [
          'earthdata.nasa.gov',
          'https://www.earthdata.nasa.gov/engage/open-data-services-software-policies/data-use-guidance',
        ],
        [
          'sentinels.copernicus.eu',
          'https://sentinels.copernicus.eu/documents/247904/690755/Sentinel_Data_Legal_Notice',
        ],
        ['data.humdata.org', 'https://data.humdata.org/dataset/viet-nam-administrative-boundaries-polygon-polyline'],
      ]),
    );
    expect(links).toHaveLength(4);
  });

  it('writes the values in the language of the page, with the m² sign', () => {
    const vi = register(['vi-VN']).textContent ?? '';
    expect(vi).toContain('1.000 m²');
    expect(vi).toContain('Nhóm Miaudow');
    expect(vi).not.toContain('Miaudow team');
    cleanup();
    const en = register(['en-US']).textContent ?? '';
    expect(en).toContain('1,000 m²');
    expect(en).toContain('Miaudow team');
  });
});
