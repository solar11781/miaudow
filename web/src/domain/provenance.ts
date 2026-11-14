// Every number the app shows belongs to one evidence kind. The kinds are never mixed silently:
// data (as published) -> derived (our arithmetic) -> study / standard (published findings) -> model -> assistant text.

export type EvidenceKind = 'data' | 'derived' | 'study' | 'standard' | 'model' | 'assistant' | 'illustration';

export const EVIDENCE_ORDER: readonly EvidenceKind[] = ['data', 'derived', 'study', 'standard', 'model', 'assistant'];

export interface Bilingual {
  vi: string;
  en: string;
}

export type SourceId =
  | 'p02'
  | 'p03'
  | 'qd18'
  | 'tcvn8641'
  | 'fao-tm3'
  | 'nasa-power'
  | 'modis'
  | 'nso'
  | 'geoboundaries'
  | 'e012'
  | 'e010'
  | 'zhang2011'
  | 'team-photos';

export interface SourceRecord {
  id: SourceId;
  kind: EvidenceKind;
  short: string;
  title: Bilingual;
  publisher: Bilingual;
  where: Bilingual;
  period: Bilingual;
  method: Bilingual;
  howRead: Bilingual;
  caveat: Bilingual;
  url?: string;
  licence?: Bilingual;
}

/** What a source button hands to the provenance sheet. */
export interface SourceRef {
  sourceId: SourceId;
  kind: EvidenceKind;
  /** The value exactly as displayed. */
  value: string;
  /** What the value is about, in the reader's language. */
  label: string;
  /** Optional extra line, e.g. the arithmetic behind a derived number. */
  detail?: string;
  /** Upstream sources of a derived number, in order. */
  chain?: SourceId[];
}
