// The evidence desk reads the rulebook (data/canonical/rotations.generated.json): its page references are
// written in the language of the page (visual audit, 2026-11-16).
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
});
