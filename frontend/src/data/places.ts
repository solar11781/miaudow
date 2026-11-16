// The places drawn on the maps, one set of coordinates for every map (D-191); their names are in the text files
// (places). The trial site is the Lưu Sơn commune marker of the data file (Wikidata Q10788283), not the trial field.
import doLuongJson from '@data/geo_do_luong.json';

export interface MapPlace {
  id: 'vinh' | 'trial';
  name: 'vinh' | 'trialSite';
  lat: number;
  lon: number;
  /** A rounded position, marked "≈" on the flat map. */
  approx: boolean;
}

const { lat, lon } = doLuongJson.study_point;
export const TRIAL_SITE: MapPlace = { id: 'trial', name: 'trialSite', lat, lon, approx: false };
// rounded city centre, for orientation only
const VINH: MapPlace = { id: 'vinh', name: 'vinh', lat: 18.68, lon: 105.68, approx: true };
export const MAP_PLACES: MapPlace[] = [VINH, TRIAL_SITE];

/** Ground length of a degree of longitude over a degree of latitude at Nghệ An (cos 19.3 degrees), for the flat and 3D maps. */
export const K_LON = Math.cos((19.3 * Math.PI) / 180);
