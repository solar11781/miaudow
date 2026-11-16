import type { WaterSituation } from '../../api';
import { RANKING } from './answer';
import { normalize } from './normalize';

export interface NextStep {
  /** ranking: the asker wants Miaudow to choose; field: the question is about the asker's own field. */
  kind: 'ranking' | 'field';
  land: WaterSituation | null;
}

// a question about the asker's own field, matched without accents; close to the server's OWN_FIELD
// (src/fieldshift/api/copilot.py), which gives such a question its fixed answer
const OWN_FIELD =
  /\b(ruong (nha |cua )?(toi|minh|em)|nha (toi|minh|em)|(toi|em|minh) trong|my (own )?(field|farm|plot|land|paddy)s?|if i|will i|i (plant|grow|earn))\b/;
const LANDS: [RegExp, WaterSituation][] = [
  [/\b(cuoi kenh|end of the canal|canal end|tail end)\b/, 'canal_end'],
  [/\b(ruong cao|cao cuong|high field|high ground|higher ground)\b/, 'high_field'],
  [/\b(thieu nuoc|hay thieu|short of water|water short|dry field)\b/, 'water_short'],
  [/\b(chu dong (duoc )?nuoc|du nuoc|reliable water)\b/, 'reliable'],
];

/** What the assistant adds under an answer: a way into the four-step comparison, with the field type the question names. */
export function nextStep(question: string, water: WaterSituation | null): NextStep | null {
  const q = normalize(question);
  const kind = RANKING.test(q) ? 'ranking' : OWN_FIELD.test(q) ? 'field' : null;
  if (!kind) return null;
  return { kind, land: LANDS.find(([re]) => re.test(q))?.[1] ?? water };
}
