import type { RiskItem, SourceId } from '../types';

/** The plain line of the card that stands for a risk quote (D-187); its text is farmer.considerations[key]. */
export type Consideration = 'cost' | 'market' | 'fodder' | 'riceZone' | 'stillRice' | 'provincePlan';

// each quote of rules/rotations.yaml by the source it quotes and words of its own, so an edited or new quote matches
// no line and the card shows it in full
const QUOTES: { key: Consideration; source: SourceId; words: string }[] = [
  { key: 'cost', source: 'R-P02', words: 'gấp 2 - 3 lần' },
  { key: 'market', source: 'R-P03', words: 'đậu tương, cây vừng' },
  { key: 'fodder', source: 'R-C13', words: 'ngô sinh khối' },
  { key: 'riceZone', source: 'R-G06', words: 'Điều 6.1' },
  { key: 'stillRice', source: 'R-G06', words: 'Điều 6.4' },
  { key: 'provincePlan', source: 'R-G27', words: 'Điều 7.1' },
];

/** The plain line of a risk quote, or null when the quote has none. */
export function consideration(risk: RiskItem): Consideration | null {
  return QUOTES.find((q) => risk.source_ids.includes(q.source) && risk.text.vi.includes(q.words))?.key ?? null;
}
