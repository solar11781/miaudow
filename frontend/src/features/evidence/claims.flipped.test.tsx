// The model claims follow the run's results: with spring and winter swapped, the sentences swap too (ML-DESIGN §5b).
import { describe, expect, it, vi as vitest } from 'vitest';
import { renderHook } from '@testing-library/react';
import type { ReactNode } from 'react';
import { SettingsProvider } from '../../app/settings';
import { ProvenanceProvider } from '../provenance/ProvenanceProvider';
import { useClaims } from './claims';

vitest.mock('../../data', async (load) => {
  const data = await load<typeof import('../../data')>();
  const made = (season: string) => season === 'spring';
  return {
    ...data,
    model: {
      ...data.model,
      weather_claims: data.model.weather_claims.map((c) => ({ ...c, made: made(c.season) })),
      seasons: data.model.seasons.map((s) =>
        s.season === 'summer_autumn' ? s : { ...s, model_status: made(s.season) ? 'shown' : 'not_shown' },
      ),
    },
  };
});

const wrapper = ({ children }: { children: ReactNode }) => (
  <SettingsProvider>
    <ProvenanceProvider>{children}</ProvenanceProvider>
  </SettingsProvider>
);

describe('evidence claims with swapped results', () => {
  it('say weather helps spring rice and does not help winter rice', () => {
    const { result } = renderHook(() => useClaims(), { wrapper });
    const spring = result.current.find((c) => c.id === 'model-spring');
    const winter = result.current.find((c) => c.id === 'model-winter');
    expect(spring?.conclusion.en).toBe(
      'For spring rice, the weather model predicts slightly better than the no-weather model.',
    );
    expect(winter?.conclusion.en).toBe('Adding weather to the model does not predict winter rice yields better.');
    expect(winter?.meaning.en).toBe('So Miaudow shows no winter rice prediction. A negative result is evidence too.');
  });
});
