/** The status words of REFERENCES.md ("READ", "ABSTRACT", "SUMMARY", "NOT READ") and the words of their details, as
 * the sheet's text keys name them. */
export interface ReadStatusLabels {
  READ: string;
  ABSTRACT: string;
  SUMMARY: string;
  NOT_READ: string;
  /** Fixed detail phrases of the register, e.g. "full text", "data", "licence unclear". */
  details: Record<string, string>;
  /** "VJOL copy <id>": the id stays data. */
  vjolCopy: (id: string) => string;
  /** "ch. <range>": the chapter range stays data. */
  chapters: (range: string) => string;
}

const KEY: Record<string, 'READ' | 'ABSTRACT' | 'SUMMARY' | 'NOT_READ'> = {
  READ: 'READ',
  ABSTRACT: 'ABSTRACT',
  SUMMARY: 'SUMMARY',
  'NOT READ': 'NOT_READ',
};
const WORD = /^(NOT READ|READ|ABSTRACT|SUMMARY)/;

/** One detail phrase in the reader's language; dates, ids and names it does not know stay as written. */
function detail(phrase: string, labels: ReadStatusLabels): string {
  const vjol = /^VJOL copy (\S+)$/.exec(phrase);
  if (vjol?.[1]) return labels.vjolCopy(vjol[1]);
  const ch = /^ch\. (\S+)$/.exec(phrase);
  if (ch?.[1]) return labels.chapters(ch[1]);
  return labels.details[phrase] ?? phrase;
}

/** The text after a status word: "(a, b)" details and "; c" notes, each phrase translated on its own. */
function rest(text: string, labels: ReadStatusLabels): string {
  return text.replace(/[^(),;]+/g, (part) => {
    const phrase = part.trim();
    return phrase ? part.replace(phrase, detail(phrase, labels)) : part;
  });
}

/** A register status in the reader's language: each leading status word and each known detail phrase is translated,
 * the rest (dates, ids, names) stays as data. */
export function readStatusText(raw: string, labels: ReadStatusLabels): string {
  const parts = raw.split(' / ');
  if (!parts.every((p) => WORD.test(p))) return raw;
  return parts
    .map((p) => {
      const word = WORD.exec(p)?.[1] ?? '';
      const k = KEY[word];
      return (k ? labels[k] : word) + rest(p.slice(word.length), labels);
    })
    .join(' / ');
}
