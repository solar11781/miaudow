// ML-DESIGN §5b: what may be said about a season's model comes from the pipeline's own results (artifacts/metrics.json
// weather_claims, artifacts/risk_table.json seasons, artifacts/gates.json G4), never from fixed text.
import { describe, expect, it } from 'vitest';
import { model } from '../data';
import { modelVerdict } from './rice';

const flipped = {
  weather_claims: [
    { season: 'spring' as const, model_id: 'm1_ridge', made: true },
    { season: 'winter' as const, model_id: 'm1_ridge', made: false },
  ],
  seasons: [
    { season: 'spring' as const, model_status: 'shown' as const, model_id: 'm1_ridge' },
    { season: 'winter' as const, model_status: 'not_shown' as const, model_id: 'm1_ridge' },
  ],
  gates: [
    { gate: 'G4', season: 'spring', model_id: 'm1_ridge', passed: false },
    { gate: 'G4', season: 'winter', model_id: 'm1_ridge', passed: true },
  ],
} as unknown as Parameters<typeof modelVerdict>[1];

describe('model verdict per season', () => {
  it('follows the frozen run: spring makes no weather claim and is not shown, winter does and is shown', () => {
    expect(modelVerdict('spring')).toEqual({ weatherHelps: false, shown: false, range: false });
    expect(modelVerdict('winter')).toEqual({ weatherHelps: true, shown: true, range: true });
    expect(model.weather_claims.find((c) => c.season === 'winter')?.made).toBe(true);
  });

  it('changes with the results, not with the season', () => {
    expect(modelVerdict('spring', flipped)).toEqual({ weatherHelps: true, shown: true, range: false });
    expect(modelVerdict('winter', flipped)).toEqual({ weatherHelps: false, shown: false, range: false });
  });

  it('says nothing for a season without a model', () => {
    expect(modelVerdict('summer_autumn')).toEqual({ weatherHelps: false, shown: false, range: false });
  });
});
