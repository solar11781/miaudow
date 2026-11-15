import { describe, expect, it } from 'vitest';
import { DATASETS } from './catalog';

describe('dataset catalog', () => {
  // REFERENCES R-D06: the Copernicus Sentinel-2 L2A images of the observatory page (PR #62, hand-off item 7)
  it('cites the Sentinel-2 images by their register row R-D06', () => {
    expect(DATASETS.find((d) => d.dataset_id === 'sentinel2_l2a_do_luong_vi')?.source_id).toBe('R-D06');
  });
});
