import { describe, expect, it } from 'vitest';
import { DATASETS } from './catalog';

describe('dataset catalog', () => {
  // REFERENCES R-D06: the Copernicus Sentinel-2 L2A images of the observatory page (PR #62, hand-off item 7)
  it('cites the Sentinel-2 images by their register row R-D06', () => {
    expect(DATASETS.find((d) => d.dataset_id === 'sentinel2_l2a_do_luong_vi')?.source_id).toBe('R-D06');
  });
});

// visual audit 2026-11-16: the register of the evidence page showed English values under Vietnamese labels, and
// machine date strings
describe('the fields the data register shows', () => {
  const shown = DATASETS.flatMap((d) =>
    (['provider', 'spatial_resolution', 'temporal_coverage', 'license'] as const).map((field) => ({
      where: `${d.dataset_id}.${field}`,
      text: d[field],
    })),
  );

  it('have a Vietnamese and an English value', () => {
    for (const { where, text } of shown) {
      expect(text.vi?.trim().length, where).toBeGreaterThan(0);
      expect(text.en?.trim().length, where).toBeGreaterThan(0);
    }
  });

  // the phrases the audit read on the Vietnamese page, and the other English words of the same values
  it('have no English phrase in the Vietnamese value', () => {
    const english =
      /\b(province|test years|team artifacts|farmland-weighted|transcribed|trial plot|No restrictions|near present|ongoing|static|computed|simplified|aggregated|daily|monthly|hourly|required|quoted|source|credit|attribute|team|grid|districts|fixed map|normal|with|from)\b/;
    expect(shown.filter(({ text }) => english.test(text.vi)).map(({ where }) => where)).toEqual([]);
  });

  it('write dates the way each language reads them, never as machine strings', () => {
    const machine = /\d{4}-\d{2}-|\d{4}-\d{2}\/|T\d{2}:\d{2}|\.\.|\d{4}\/\d{4}|\d\/near/;
    const periods = DATASETS.map((d) => d.temporal_coverage);
    expect(periods.flatMap((p) => [p.vi, p.en]).filter((p) => machine.test(p))).toEqual([]);
    // the same facts as before: POWER daily 1990-01-01/2024-12-31, the P-02 trial 2020-06/2021-06
    const power = DATASETS.find((d) => d.dataset_id === 'nasa_power_daily')?.temporal_coverage;
    expect(power).toEqual({ vi: '1/1/1990 – 31/12/2024', en: '1 January 1990 – 31 December 2024' });
    const trial = DATASETS.find((d) => d.dataset_id === 'study_p02')?.temporal_coverage;
    expect(trial).toEqual({ vi: 'tháng 6/2020 – tháng 6/2021', en: 'June 2020 – June 2021' });
  });

  // D-170: Vietnamese writes a decimal comma and a dot for thousands
  it('write numbers the Vietnamese way in the Vietnamese value', () => {
    const resolution = (id: string) => DATASETS.find((d) => d.dataset_id === id)?.spatial_resolution;
    expect(resolution('nasa_power_daily')?.vi).toContain('0,5° x 0,625°');
    expect(resolution('nasa_power_daily')?.en).toContain('0.5° x 0.625°');
    expect(resolution('study_p02')?.vi).toContain('1.000 m2');
    expect(resolution('study_p02')?.en).toContain('1,000 m2');
  });
});
