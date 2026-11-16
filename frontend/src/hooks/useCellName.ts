import { useCallback } from 'react';
import { geo } from '../data';
import { useFormat, useT } from '../app/settings';

/** A grid cell named by its centre, from its id: "19,0°B 105,625°Đ" in Vietnamese, "19.0°N 105.625°E" in English.
 * The digits are the grid's own: half a degree of latitude, 0.625 of longitude. */
export function useCellName() {
  const t = useT();
  const f = useFormat();
  return useCallback(
    (id: string) => {
      const c = geo.grid.find((g) => g.id === id);
      return c ? t.science.cellAt(f.n(c.lat, 1), f.n(c.lon, 3)) : id;
    },
    [t, f],
  );
}
