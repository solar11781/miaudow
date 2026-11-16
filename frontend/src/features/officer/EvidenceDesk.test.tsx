// The evidence desk reads the rulebook (data/canonical/rotations.generated.json): its page references and its plot
// size are written the way the rest of the page writes them in each language (visual audit, 2026-11-16).
import { afterEach, describe, expect, it } from 'vitest';
import { cleanup, render } from '@testing-library/react';
import { SettingsProvider } from '../../app/settings';
import { ProvenanceProvider } from '../provenance/ProvenanceProvider';
import { EvidenceDesk } from './EvidenceDesk';

function desk(languages: string[]) {
  Object.defineProperty(window.navigator, 'languages', { value: languages, configurable: true });
  render(
    <SettingsProvider>
      <ProvenanceProvider>
        <EvidenceDesk />
      </ProvenanceProvider>
    </SettingsProvider>,
  );
  return document.body.textContent ?? '';
}

describe('officer evidence desk', () => {
  afterEach(() => {
    cleanup();
    Object.defineProperty(window.navigator, 'languages', { value: ['vi-VN', 'vi'], configurable: true });
  });
  // rules/rotations.yaml cc1 risk line 1: location "tr. 48", location_precision "page"
  it('writes the page of a quote as "p." in English and "tr." in Vietnamese', () => {
    const en = desk(['en-US', 'en']);
    expect(en).toContain('p. 48');
    expect(en).not.toContain('tr. 48');
    cleanup();
    expect(desk(['vi-VN', 'vi'])).toContain('tr. 48');
  });
  // the plot size at the top of the page (officer.scope) is "1.000 m²" in Vietnamese and "1,000 m²" in English (D-170)
  it('writes the plot size of step 5 with the thousands mark of the language and the m² sign', () => {
    const vi = desk(['vi-VN', 'vi']);
    expect(vi).toContain('1.000 m²');
    expect(vi).not.toMatch(/1000 m|m2/);
    cleanup();
    const en = desk(['en-US', 'en']);
    expect(en).toContain('1,000 m²');
    expect(en).not.toMatch(/1000 m|m2/);
  });
});
