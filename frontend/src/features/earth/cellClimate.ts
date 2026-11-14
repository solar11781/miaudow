// Annual rain of one NASA POWER cell and its anomaly against that cell's own 1991–2020 normal, from the canonical
// climate file. Kept apart from the globe so the panels work without loading CesiumJS.
import { CLIMATE } from '../../data/climate';

interface CellSeries {
  cells: Record<string, Record<string, { annual_rain_mm: number | null }>>;
}
const SERIES = (CLIMATE as unknown as { series: CellSeries }).series;
const NORMAL = (CLIMATE as unknown as { normal_mm: { cells: Record<string, number[]> } }).normal_mm.cells;

/** null when the year has an incomplete month (complete-month rule) or the cell is unknown. */
export function cellYear(cell: string, year: number): { rain: number; anomaly: number } | null {
  const rain = SERIES.cells[cell]?.[String(year)]?.annual_rain_mm ?? null;
  const normal = (NORMAL[cell] ?? []).reduce((a, b) => a + b, 0);
  if (rain === null || !normal) return null;
  return { rain, anomaly: rain / normal - 1 };
}
