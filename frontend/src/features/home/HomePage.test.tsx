// CLAUDE.md scientific boundaries and D-52: the two studies' profit values are never shown as comparable; the trial
// chapter shows one study's value with its own definition and trial label, under the study's own land words (D-160).
import { afterEach, describe, expect, it } from 'vitest';
import { cleanup, render } from '@testing-library/react';
import { SettingsProvider } from '../../app/settings';
import { ProvenanceProvider } from '../provenance/ProvenanceProvider';
import { Problem } from './HomePage';
import { vi } from '../../i18n/vi';

function renderProblem() {
  render(
    <SettingsProvider>
      <ProvenanceProvider>
        <Problem />
      </ProvenanceProvider>
    </SettingsProvider>,
  );
  const section = document.querySelector('#ch-2');
  if (!section) throw new Error('no trial chapter');
  return section;
}

describe('home trial chapter', () => {
  afterEach(cleanup);
  it('shows one money value only, from the first paper, with its definition in the tile', () => {
    const section = renderProblem();
    expect([...section.querySelectorAll('[data-value]')]).toHaveLength(1);
    const tile = section.querySelector('[data-value]')?.parentElement;
    expect(tile?.textContent).toContain(vi.farmer.definitionPlain.p02);
    expect(tile?.textContent).toContain(vi.home.riceSpring);
    expect(section.textContent).not.toContain(vi.farmer.definitionPlain.p03);
    expect(section.textContent).not.toContain('1,16'); // the second paper's value (rules/rotations.yaml usual_p03)
  });
  it('heads the chapter with the land words of the first paper, not a profit claim', () => {
    const section = renderProblem();
    // rules/rotations.yaml `usual` land_archetypes: P-02 "đất lúa kém hiệu quả, thường xuyên khô hạn" (D-160)
    expect(section.querySelector('h2')?.textContent).toBe('Đất lúa kém hiệu quả, thường xuyên khô hạn');
  });
});
