import { PASSAGES, type Passage } from './knowledge';
import { hasDiacritics, tokens } from './normalize';

// BM25 over both languages of every passage. Two indexes: one keeps Vietnamese accents (used when the question has
// them, so “máy bay” never matches “máy móc”), one strips them (for questions typed without accents, and English).
const K1 = 1.4;
const B = 0.72;

interface Doc {
  passage: Passage;
  tf: Map<string, number>;
  len: number;
}
interface Index {
  docs: Doc[];
  df: Map<string, number>;
  avg: number;
  n: number;
}

function build(passages: Passage[], accented: boolean): Index {
  const docs: Doc[] = passages.map((p) => {
    const toks = tokens(
      `${p.title.vi} ${p.title.en} ${p.title.vi} ${p.text.vi} ${p.text.en} ${p.keys} ${p.keys}`,
      accented,
    );
    const tf = new Map<string, number>();
    for (const t of toks) tf.set(t, (tf.get(t) ?? 0) + 1);
    return { passage: p, tf, len: toks.length };
  });
  const df = new Map<string, number>();
  for (const d of docs) for (const t of d.tf.keys()) df.set(t, (df.get(t) ?? 0) + 1);
  return { docs, df, avg: docs.reduce((s, d) => s + d.len, 0) / Math.max(1, docs.length), n: docs.length };
}

const ACCENTED = build(PASSAGES, true);
const PLAIN = build(PASSAGES, false);

export interface Hit {
  passage: Passage;
  score: number;
  /** Share of the question's distinct terms found in the passage (0..1). */
  coverage: number;
}

export function search(question: string, limit = 3): Hit[] {
  const accented = hasDiacritics(question);
  const idx = accented ? ACCENTED : PLAIN;
  const q = [...new Set(tokens(question, accented))];
  if (!q.length) return [];
  const hits = idx.docs.map((d) => {
    let score = 0;
    let matched = 0;
    for (const t of q) {
      const f = d.tf.get(t);
      if (!f) continue;
      matched += 1;
      const df = idx.df.get(t) ?? 0;
      const idf = Math.log(1 + (idx.n - df + 0.5) / (df + 0.5));
      score += idf * ((f * (K1 + 1)) / (f + K1 * (1 - B + (B * d.len) / idx.avg)));
    }
    return { passage: d.passage, score, coverage: matched / q.length };
  });
  return hits
    .filter((h) => h.score > 0)
    .sort((a, b) => b.score - a.score)
    .slice(0, limit);
}

/** A match is strong enough to answer from only with both a score and a term coverage above these (see ai.test.ts). */
export const MIN_SCORE = 4.5;
export const MIN_COVERAGE = 0.5;
export const isStrong = (h: Hit) => h.score >= MIN_SCORE && h.coverage >= MIN_COVERAGE;
