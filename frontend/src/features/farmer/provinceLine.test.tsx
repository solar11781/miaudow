// UI-UX-SPEC section 7 "Province line" and FR-01 (D-183): the field step shows a locked province selector with one
// option, Nghệ An, reachable by screen readers (aria-disabled, not disabled), with a note that no other province exists
import { afterEach, describe, expect, it } from 'vitest';
import { cleanup, fireEvent, render, screen } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { SettingsProvider } from '../../app/settings';
import { FarmerLayout } from './FarmerLayout';
import { LandStep } from './LandStep';
import { vi as text } from '../../i18n/vi';

describe('province line', () => {
  afterEach(cleanup);
  it('shows Nghệ An as the only, locked choice with its note', () => {
    render(
      <SettingsProvider>
        <MemoryRouter initialEntries={['/nong-dan/ruong']}>
          <Routes>
            <Route element={<FarmerLayout />}>
              <Route path="/nong-dan/ruong" element={<LandStep />} />
            </Route>
          </Routes>
        </MemoryRouter>
      </SettingsProvider>,
    );
    const select = screen.getByRole('combobox', { name: text.farmer.province });
    expect(select.getAttribute('aria-disabled')).toBe('true');
    expect(select.hasAttribute('disabled')).toBe(false);
    expect([...select.querySelectorAll('option')].map((o) => o.textContent)).toEqual(['Nghệ An']);
    fireEvent.change(select, { target: { value: 'other' } });
    expect((select as HTMLSelectElement).value).toBe('nghe_an');
    expect(screen.getByText(text.farmer.provinceNote)).toBeTruthy();
  });
});
