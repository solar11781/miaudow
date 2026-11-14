// A data line names only the datasets the response cites (H19; D-169: never a dataset we did not use).
import { describe, expect, it } from 'vitest';
import { vi as text } from '../i18n/vi';
import { dataNames } from './dataLine';

const cited = (...ids: string[]) => Object.fromEntries(ids.map((id) => [id, {}]));

describe('data line', () => {
  it('names the datasets of the past-years response only', () => {
    expect(dataNames(cited('E-019', 'R-A01', 'R-N01', 'R-N02'), text.farmer.dataSources)).toEqual([
      'NASA POWER',
      'NASA MODIS',
    ]);
  });
  it('names a study once even when two of its papers are cited', () => {
    const names = dataNames(cited('R-N01', 'R-D01', 'R-P02', 'R-P03', 'R-W15'), text.farmer.dataSources);
    expect(names).toEqual(['NASA POWER', 'Cục Thống kê', 'Trịnh Đức Toàn và cs. (2023)']);
  });
  it('never names a dataset the response does not cite', () => {
    expect(dataNames(cited('R-N01'), text.farmer.dataSources).join(' ')).not.toMatch(/CHIRPS|MODIS|IMERG/);
  });
  it('leaves out datasets cited only as considered and not used', () => {
    expect(dataNames(cited('R-N05', 'R-N09', 'R-N10'), text.farmer.dataSources)).toEqual(['NASA GPM IMERG']);
  });
});
