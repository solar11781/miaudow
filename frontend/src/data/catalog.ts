// The dataset catalog (contract `Dataset` in api/miaudow_api/contracts.py). Read from the canonical build so the web
// app and the API show the same ingestion state.
import catalogJson from '@data/catalog.json';
import type { Bilingual } from '../domain/provenance';

export type IngestionStatus = 'INGESTED' | 'PARTIAL' | 'CONTRACT_ONLY' | 'BLOCKED';

export interface DatasetInfo {
  dataset_id: string;
  title: Bilingual;
  provider: string;
  source_id: string;
  source_url: string | null;
  license: string;
  temporal_coverage: string;
  spatial_resolution: string;
  ingestion_status: IngestionStatus;
  is_field_measurement: boolean;
  notes: Bilingual[];
}

interface Catalog {
  generated_at: string;
  datasets: DatasetInfo[];
}

export const CATALOG = catalogJson as unknown as Catalog;
export const DATASETS: DatasetInfo[] = CATALOG.datasets;
