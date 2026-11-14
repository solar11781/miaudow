// D-52 and UI-UX-SPEC section 9 money row: the second paper's money (P-03) is never framed like the first paper's
// (P-02) yearly sums; each study's value carries its own label and definition, and the column says these are trial
// figures.
import { afterEach, describe, expect, it } from 'vitest';
import { cleanup, render } from '@testing-library/react';
import { SettingsProvider } from '../../app/settings';
import { ProvenanceProvider } from '../provenance/ProvenanceProvider';
import { Matrix } from './OfficerPage';
import { vi } from '../../i18n/vi';

function rows() {
  render(
    <SettingsProvider>
      <ProvenanceProvider>
        <Matrix />
      </ProvenanceProvider>
    </SettingsProvider>,
  );
  return [...document.querySelectorAll('tbody tr')].map((r) => r.querySelectorAll('td')[0]?.textContent ?? '');
}

describe('officer evidence matrix', () => {
  afterEach(cleanup);
  it('heads the money column as trial figures, not a yearly profit', () => {
    rows();
    const head = document.querySelectorAll('thead th')[1]?.textContent ?? '';
    expect(head).toContain('thử nghiệm');
    expect(head).not.toContain('cả năm');
  });
  it('gives the second paper its own label and definition, without a yearly framing', () => {
    const money = rows();
    const p03 = money.filter((m) => m.includes('1,16'));
    expect(p03).toHaveLength(1);
    expect(p03[0]).toContain(vi.officer.p03Money);
    expect(p03[0]).toContain(vi.farmer.definitionPlain.p03);
    expect(p03[0]).not.toContain(vi.farmer.definitionPlain.p02);
    expect(p03[0]).not.toContain('cả năm');
    const p02 = money.filter((m) => !m.includes('1,16'));
    expect(p02).toHaveLength(5); // the farmers' usual plan and CC1-CC4 (rules/rotations.yaml)
    for (const m of p02) {
      expect(m).toContain(vi.farmer.definitionPlain.p02);
      expect(m).not.toContain(vi.farmer.definitionPlain.p03);
    }
  });
});
