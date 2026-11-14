// D-165: the winter weather result is "narrow" and "fragile" wherever it appears, in the method report's words.
import { describe, expect, it } from 'vitest';
import { renderHook } from '@testing-library/react';
import type { ReactNode } from 'react';
import { SettingsProvider } from '../../app/settings';
import { ProvenanceProvider } from '../provenance/ProvenanceProvider';
import { useClaims } from './claims';
import { vi } from '../../i18n/vi';
import { en } from '../../i18n/en';

const wrapper = ({ children }: { children: ReactNode }) => (
  <SettingsProvider>
    <ProvenanceProvider>{children}</ProvenanceProvider>
  </SettingsProvider>
);

describe('evidence claims', () => {
  it('say the winter weather result is narrow and fragile', () => {
    const { result } = renderHook(() => useClaims(), { wrapper });
    const winter = result.current.find((c) => c.id === 'model-winter');
    expect(winter?.meaning.vi).toContain(vi.common.winterFragile);
    expect(winter?.meaning.en).toContain(en.common.winterFragile);
  });
  // UI-UX-SPEC §9: TCVN 8641's measure is "nước phải tưới vào ruộng" (water to apply), not what the crop needs
  it('use the standard term for the TCVN water', () => {
    const { result } = renderHook(() => useClaims(), { wrapper });
    const water = result.current.find((c) => c.id === 'water-rice-peanut');
    expect(water?.conclusion.vi).toContain('nước phải tưới');
    expect(water?.conclusion.en).toContain('water to apply');
    expect(water?.conclusion.en).not.toContain('needs');
  });
});
