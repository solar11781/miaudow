/** The status words of REFERENCES.md ("READ", "ABSTRACT", "SUMMARY", "NOT READ"), as the sheet's text keys name them. */
export interface ReadStatusLabels {
  READ: string;
  ABSTRACT: string;
  SUMMARY: string;
  NOT_READ: string;
}

const KEY: Record<string, keyof ReadStatusLabels> = {
  READ: 'READ',
  ABSTRACT: 'ABSTRACT',
  SUMMARY: 'SUMMARY',
  'NOT READ': 'NOT_READ',
};
const WORD = /^(NOT READ|READ|ABSTRACT|SUMMARY)/;

/** A register status in the reader's language: each leading status word is translated, the rest stays as data. */
export function readStatusText(raw: string, labels: ReadStatusLabels): string {
  const parts = raw.split(' / ');
  if (!parts.every((p) => WORD.test(p))) return raw;
  return parts
    .map((p) =>
      p.replace(WORD, (w) => {
        const k = KEY[w];
        return k ? labels[k] : w;
      }),
    )
    .join(' / ');
}
