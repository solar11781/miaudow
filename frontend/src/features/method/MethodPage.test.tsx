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
import { en } from '../../i18n/en';
import { vi } from '../../i18n/vi';

function renderPage(languages: string[] = ['vi-VN', 'vi'], res: unknown = method) {
  Object.defineProperty(window.navigator, 'languages', { value: languages, configurable: true });
  mock.spyOn(api, 'method').mockResolvedValue(validateMethod(res));
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

/** The scope ("Phạm vi") cell of every result row: the second cell after the row heading. */
function scopeCells() {
  return new Set([...document.querySelectorAll('#main tbody tr > td:nth-of-type(2)')].map((c) => c.textContent));
}

describe('method page', () => {
  afterEach(() => {
    cleanup();
    mock.restoreAllMocks();
    Object.defineProperty(window.navigator, 'languages', { value: ['vi-VN', 'vi'], configurable: true });
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
  // visual audit of the method page: data keys ("Nghe An", "red_river_delta") were printed as the scope of a row.
  // Vietnamese names as the statistics office writes them; English without accent marks (D-186, D-191).
  it.each([
    [
      ['vi-VN', 'vi'],
      [
        'Nghệ An',
        'Hà Tĩnh',
        'Thanh Hóa',
        'Đồng bằng sông Hồng',
        'Trung du và miền núi phía Bắc',
        'Bắc Trung Bộ và Duyên hải miền Trung',
        'Tây Nguyên',
        'Đông Nam Bộ',
        'Đồng bằng sông Cửu Long',
      ],
    ],
    [
      ['en-GB', 'en'],
      [
        'Nghe An',
        'Ha Tinh',
        'Thanh Hoa',
        'Red River Delta',
        'Northern midlands and mountain areas',
        'North Central and Central coastal areas',
        'Central Highlands',
        'South East',
        'Mekong River Delta',
      ],
    ],
  ])('names the provinces and regions in the reading language (%s)', async (languages, names) => {
    renderPage(languages);
    await screen.findByRole('heading', { level: 2, name: (languages[1] === 'vi' ? vi : en).method.metricsTitle });
    const scopes = scopeCells();
    for (const name of names) expect(scopes).toContain(name);
    expect([...scopes].filter((c) => c?.includes('_') || (languages[1] === 'vi' && c === 'Nghe An'))).toEqual([]);
  });
  it('still shows a scope it has no name for', async () => {
    const rows = method.metrics.map((r, i) => (i === 0 ? { ...r, subset: 'region:new_area' } : r));
    renderPage(['vi-VN', 'vi'], { ...method, metrics: rows });
    await screen.findByRole('heading', { level: 2, name: vi.method.metricsTitle });
    expect(scopeCells()).toContain('new_area');
  });
  // visual audit of the method page: about 40,000 px tall; the per-province and per-region rows fold, closed at first
  it('folds the per-province and per-region rows and keeps the headline rows open', async () => {
    renderPage();
    await screen.findByRole('heading', { level: 2, name: vi.method.metricsTitle });
    const folds = [...document.querySelectorAll<HTMLDetailsElement>('#main details')].filter(
      (d) => d.querySelector('summary')?.textContent === vi.method.breakdown,
    );
    expect(folds).toHaveLength(2); // spring and winter rice
    const headline = new Set([vi.method.subsets.national, vi.method.subsets.na_ht_th]);
    for (const fold of folds) {
      expect(fold.open).toBe(false);
      const scopes = [...fold.querySelectorAll('tbody tr > td:nth-of-type(2)')].map((c) => c.textContent ?? '');
      expect(scopes).toHaveLength(36); // 4 models x (3 provinces + 6 regions)
      expect(scopes.filter((c) => headline.has(c))).toEqual([]);
    }
    const open = [...document.querySelectorAll('[data-testid^="metric-row-"]')].flatMap((cell) => {
      const row = cell.closest('tr');
      return row && !row.closest('details') ? [row] : [];
    });
    expect(open.length).toBeGreaterThan(0);
    for (const row of open) expect(headline).toContain(row.querySelector('td:nth-of-type(2)')?.textContent);
    expect(open.some((r) => r.querySelector('td')?.textContent === vi.method.role.primary)).toBe(true);
  });
});
