// UI-UX-SPEC section 8 item 2 and section 10 "Rule mode" (T18): one "?" legend button per rule on /nong-dan/nam,
// `legend-<rule code>`, named by `common.sourceFor`, opening the source sheet with the rule text and its sources
import { afterEach, describe, expect, it, vi as mock } from 'vitest';
import { cleanup, fireEvent, render, screen, within } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { SettingsProvider } from '../../app/settings';
import { ProvenanceProvider } from '../provenance/ProvenanceProvider';
import { api, validatePastYears } from '../../api';
import { facts, pastYears } from '../../tests/fixtures';
import { RULE_CODES } from '../../types';
import { FarmerLayout } from './FarmerLayout';
import { YearsStep } from './YearsStep';
import { vi as text } from '../../i18n/vi';

const named = (id: string) => ({ ...facts(id), citation: { vi: `trích ${id}`, en: `cite ${id}` } });

function response() {
  const raw = pastYears();
  return validatePastYears({
    ...raw,
    rules: raw.rules.map((r) => ({
      ...r,
      label: { vi: `nhãn ${r.code}`, en: `label ${r.code}` },
      rule_text: { vi: `lời ${r.code}`, en: `text ${r.code}` },
      values_source_ids: ['R-N01', 'R-N02'],
    })),
    sources: { ...raw.sources, 'R-A01': named('R-A01'), 'R-N01': named('R-N01'), 'R-N02': named('R-N02') },
  });
}

function renderYears(res = response()) {
  mock.spyOn(api, 'pastYears').mockResolvedValue(res);
  render(
    <SettingsProvider>
      <ProvenanceProvider>
        <MemoryRouter initialEntries={['/nong-dan/nam']}>
          <Routes>
            <Route element={<FarmerLayout />}>
              <Route path="/nong-dan/nam" element={<YearsStep />} />
            </Route>
          </Routes>
        </MemoryRouter>
      </ProvenanceProvider>
    </SettingsProvider>,
  );
}

describe('years step legend', () => {
  afterEach(() => {
    cleanup();
    mock.restoreAllMocks();
  });
  it('has one "?" button per rule, in the order of rules, named by the rule label', async () => {
    renderYears();
    await screen.findAllByTestId(/^legend-/);
    const buttons = screen.getAllByTestId(/^legend-/);
    expect(buttons.map((b) => b.getAttribute('data-testid'))).toEqual(RULE_CODES.map((c) => `legend-${c}`));
    for (const code of RULE_CODES)
      expect(screen.getByRole('button', { name: text.common.sourceFor(`nhãn ${code}`) }).dataset.testid).toBe(
        `legend-${code}`,
      );
  });
  it('opens the source sheet in rule mode: the rule text, R-A01, R-N01, R-N02 and the computed note', async () => {
    renderYears();
    const code = RULE_CODES[0];
    fireEvent.click(await screen.findByTestId(`legend-${code}`));
    const sheet = within(screen.getByTestId('source-sheet'));
    expect(sheet.getByRole('heading', { name: `nhãn ${code}` })).toBeTruthy();
    for (const part of [text.sheet.ruleText, `lời ${code}`, 'trích R-A01', 'trích R-N01', 'trích R-N02'])
      expect(sheet.getByText(part)).toBeTruthy();
    expect(sheet.getByText(text.common.computedNote)).toBeTruthy();
  });
  // visual audit 2026-11-16: the limits fold had no marker; it shows the plan cards' chevron
  it('marks the limits fold with a chevron', async () => {
    renderYears();
    const summary = (await screen.findByText(text.farmer.limitsTitle)).closest('summary');
    expect(summary?.querySelector('svg:last-child')).not.toBeNull();
  });
  // roleplay audit 2026-11-16 (farmer): the years are the task, the rule names are reference; the legend sat above
  // the years, and after "pick the hardest years" nothing on screen changed
  it('puts the year buttons before the legend', async () => {
    renderYears();
    const legend = (await screen.findAllByTestId(/^legend-/))[0];
    const year = screen.getByTestId('year-1995');
    expect(legend && year.compareDocumentPosition(legend) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
  });
  it('brings the first picked year on screen after "pick the hardest years for me"', async () => {
    const scrolled: string[] = [];
    Element.prototype.scrollIntoView = function scrollIntoView(this: Element) {
      scrolled.push(this.id);
    };
    // 1996 is the year each rule covered the most farmland
    const res = response();
    const share = (value: string) => ({ value, unit: { vi: '%', en: '%' }, source_ids: ['R-N01'] });
    renderYears({
      ...res,
      years: res.years.map((y) => ({
        ...y,
        shares: Object.fromEntries(RULE_CODES.map((c) => [c, share(y.year === 1996 ? '80' : '10')])),
      })) as typeof res.years,
    });
    fireEvent.click(await screen.findByRole('button', { name: text.farmer.hardYears }));
    await screen.findByRole('article');
    expect(scrolled).toContain('year-card-1996');
  });
});
