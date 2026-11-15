// D-191: every map marks the trial site at the sourced Lưu Sơn commune marker of data/canonical/geo_do_luong.json
// (Wikidata Q10788283), labelled Lưu Sơn; CLAUDE.md standard 5: no inline user-visible text in the map and chart code.
import { afterEach, describe, expect, it } from 'vitest';
import { cleanup, render } from '@testing-library/react';
import { SettingsProvider } from '../../app/settings';
import { vi } from '../../i18n/vi';
import { en } from '../../i18n/en';
import { Grid3D } from './Grid3D';
import { MAP_PLACES } from '../../data/places';
import grid3dSource from './Grid3D.tsx?raw';
import sceneSource from './observatoryScene.ts?raw';
import globeSource from '../earth/globe.ts?raw';
import rainSource from '../charts/RainStrip.tsx?raw';
import twoSource from '../charts/TwoSources.tsx?raw';

// geo_do_luong.json study_point
const STUDY_POINT = { lat: 18.89638889, lon: 105.2802778 };

describe('trial site on the maps', () => {
  afterEach(cleanup);
  it('put the shared trial site at the study point, named Lưu Sơn', () => {
    const site = MAP_PLACES.find((p) => p.id === 'trial');
    expect(site && { lat: site.lat, lon: site.lon }).toEqual(STUDY_POINT);
    expect(site && vi.places[site.name]).toBe('Lưu Sơn (cũ) · nơi thử nghiệm');
  });
  it('labels the trial site Lưu Sơn on the flat map', () => {
    render(
      <SettingsProvider>
        <Grid3D rule="heat" year={2010} selected="" onSelect={() => undefined} />
      </SettingsProvider>,
    );
    expect(document.body.textContent).toContain(vi.places.trialSite);
    expect(document.body.textContent).not.toContain('Đô Lương · nơi thử nghiệm');
  });
  it('take the places of the science maps from the shared list, with no typed coordinates', () => {
    for (const src of [grid3dSource, sceneSource]) {
      expect(src).toContain("from '../../data/places'");
      expect(src).not.toMatch(/lat: \d/);
    }
  });
  it('keep no inline Vietnamese or English text in the map and chart code', () => {
    for (const src of [grid3dSource, sceneSource, globeSource, rainSource, twoSource]) {
      expect(src).not.toMatch(/vi \? ['`]/);
      expect(src).not.toMatch(/lang === 'vi' \? ['`]/);
      expect(src).not.toMatch(/\bvi: '/);
    }
  });
});

// member A, 2026-11-15: the globe that shows Vietnam marks Hoang Sa, Truong Sa and Phu Quoc, at their Wikidata points
// (Q274388, Q215664, Q146695), with the Vietnamese and English names member A chose
describe('islands on the globe', () => {
  it('label Hoang Sa, Truong Sa and Phu Quoc at their sourced points', () => {
    expect(vi.places.hoangSa).toBe('QĐ. Hoàng Sa (Việt Nam)');
    expect(vi.places.truongSa).toBe('QĐ. Trường Sa (Việt Nam)');
    expect(vi.places.phuQuoc).toBe('Đảo Phú Quốc');
    expect(en.places.hoangSa).toBe('Hoang Sa (Paracel) Archipelago, Vietnam');
    expect(en.places.truongSa).toBe('Truong Sa (Spratly) Archipelago, Vietnam');
    expect(en.places.phuQuoc).toBe('Phu Quoc Island');
    const flat = globeSource.replace(/\s+/g, '');
    expect(flat).toContain(
      'vi:twoLines(vi.places.hoangSa),en:twoLines(en.places.hoangSa),lat:16.654612,lon:112.747192',
    );
    expect(flat).toContain('vi:twoLines(vi.places.truongSa),en:twoLines(en.places.truongSa),lat:10,lon:114');
    expect(flat).toContain('vi:vi.places.phuQuoc,en:en.places.phuQuoc,lat:10.228889,lon:103.957222');
  });
});
