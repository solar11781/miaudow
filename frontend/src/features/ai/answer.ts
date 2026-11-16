import { YEARS } from '../../data';
import { FARMER_RULES, RULES, yearShare } from '../../domain/hazards';
import { CROPS, PLANS, planLabel, planProfitMillion, type CropId, type CropInfo } from '../../domain/plans';
import { en } from '../../i18n/en';
import { vi as viText } from '../../i18n/vi';
import { riceYear } from '../../domain/rice';
import type { EvidenceKind, SourceRef } from '../../domain/provenance';
import { SOURCES } from '../../domain/sources';
import { PASSAGES, type Passage } from './knowledge';
import { normalize } from './normalize';
import { isStrong, search, type Hit } from './retrieve';

export type Lang = 'vi' | 'en';

export interface Fmt {
  pct: (share: number) => string;
  signedPct: (share: number) => string;
  n: (v: number, digits?: number) => string;
}

export interface AnswerLine {
  text: string;
  ref?: SourceRef;
}

export interface Answer {
  type: 'year' | 'crop' | 'no-ranking' | 'evidence' | 'abstain';
  lines: AnswerLine[];
  evidence: Hit[];
  kinds: EvidenceKind[];
}

/** A question that asks Miaudow to choose a crop or a plan. */
export const RANKING =
  /\b(nen trong|trong gi|tot nhat|nen chon|chon cay|cay nao|lai nhat|best|should i grow|what to grow|which crop|recommend)\b/;
const FORECAST =
  /\b(ngay mai|tuan toi|tuan sau|thang toi|thang sau|mua toi|mua sau|nam toi|nam sau|du bao|tomorrow|next (week|month|season|year)|forecast)\b/;
const YEAR = /\b(19\d\d|20\d\d)\b/;
const CROP_WORDS: [RegExp, CropId][] = [
  [/\b(lac|dau phong|peanut)\b/, 'peanut'],
  [/\b(dau xanh|mung)\b/, 'mung'],
  [/\b(dau tuong|soy)/, 'soy'],
  [/\b(dau den|black bean)\b/, 'blackbean'],
  [/\b(ngo sinh khoi|biomass)\b/, 'biomaize'],
  [/\b(ngo|maize|corn)\b/, 'maize'],
  [/\b(khoai lang|sweet potato)\b/, 'sweetpotato'],
  [/\b(vung|sesame)\b/, 'sesame'],
  [/\b(bi do|pumpkin)\b/, 'pumpkin'],
  [/\b(ot|chili)\b/, 'chili'],
];

/** A passage as answer lines: its text with the button of its first source, then one line per further source (H5). */
function passageLines(p: Passage, lang: Lang): AnswerLine[] {
  const ref = (id: Passage['sources'][number]): SourceRef => ({
    sourceId: id,
    kind: SOURCES[id].kind,
    value: SOURCES[id].short[lang],
    label: p.title[lang],
  });
  const [first, ...rest] = p.sources;
  return [
    { text: `${p.title[lang]} — ${p.text[lang]}`, ref: first ? ref(first) : undefined },
    ...rest.map((id) => ({ text: SOURCES[id].title[lang], ref: ref(id) })),
  ];
}

function yearAnswer(year: number, lang: Lang, f: Fmt): Answer {
  const vi = lang === 'vi';
  if (!YEARS.includes(year)) {
    return {
      type: 'abstain',
      lines: [
        {
          text: vi
            ? `Miaudow chỉ có số liệu các năm ${YEARS[0]}–${YEARS[YEARS.length - 1]}.`
            : `Miaudow only has data for ${YEARS[0]}–${YEARS[YEARS.length - 1]}.`,
        },
      ],
      evidence: [],
      kinds: [],
    };
  }
  const lines: AnswerLine[] = [
    {
      text: vi
        ? `Năm ${year}, phần đất trồng Nghệ An gặp điều kiện theo QĐ 18/2021, trong thời gian có cây của thử nghiệm Trịnh Đức Toàn và cs. (2023) trên ruộng:`
        : `In ${year}, share of Nghệ An farmland meeting each Decision 18/2021 condition while the crops of the Trịnh Đức Toàn et al. (2023) trial were in the field:`,
    },
  ];
  for (const rule of FARMER_RULES) {
    const v = yearShare(rule, year);
    lines.push({
      text: `${RULES[rule].name[lang]} (${RULES[rule].article[lang]})`,
      ref: {
        sourceId: 'nasa-power',
        kind: 'derived',
        value: f.pct(v),
        label: `${RULES[rule].name[lang]} · ${year}`,
        chain: ['nasa-power', 'qd18', 'modis'],
      },
    });
  }
  const rice = riceYear('spring', year);
  if (rice.actual !== null) {
    lines.push({
      text: vi ? 'Lúa vụ Đông Xuân cả tỉnh so với bình thường' : 'Province spring rice against normal',
      ref: {
        sourceId: 'nso',
        kind: 'data',
        value: f.signedPct(rice.actual),
        label: vi ? `Lúa vụ Đông Xuân ${year}` : `Spring rice ${year}`,
        chain: ['nso', 'e010'],
      },
    });
  }
  lines.push({
    text: vi
      ? 'Đây là năm đã qua, không phải dự báo. Số liệu từ ô lưới khoảng 55 × 66 km, không đo ruộng nhà bạn.'
      : 'This is a past year, not a forecast. Values come from cells of about 55 × 66 km, not your field.',
  });
  return { type: 'year', lines, evidence: [], kinds: ['data', 'derived'] };
}

function cropAnswer(crop: CropId, lang: Lang, f: Fmt): Answer {
  const vi = lang === 'vi';
  const t = vi ? viText : en;
  const rows = PLANS.flatMap((p) => p.crops.filter((c) => c.crop === crop).map((c) => ({ p, c })));
  const name = CROPS[crop].name[lang];
  const lines: AnswerLine[] = [
    {
      text: vi
        ? `${name} trong thử nghiệm 2020–21 của Trịnh Đức Toàn và cs. (2023), lãi đã trừ công:`
        : `${name} in the 2020–21 trial of Trịnh Đức Toàn et al. (2023), profit net of labour:`,
    },
  ];
  for (const { p, c } of rows) {
    lines.push({
      text: [planLabel(p, t.farmer), c.variety, `${c.sow} → ${c.harvest}`].filter(Boolean).join(' · '),
      ref: {
        sourceId: 'p02',
        kind: 'study',
        // million dong per ha as farmers read it (D-190); the detail keeps the paper's thousand values
        value: `${f.n(c.profit / 1000, 1)} ${t.common.millionPerHa}`,
        label: `${name} ${c.variety}`.trim(),
        detail: t.refs.cropProfitDetail(f.n(c.profit), f.n(c.cost), f.n(c.price)),
      },
    });
  }
  const info: CropInfo = CROPS[crop];
  const tcvnRows = info.tcvn ?? [];
  if (tcvnRows.length) {
    for (const r of tcvnRows) {
      const scope = r.scope ? ` (${r.scope[lang]})` : '';
      lines.push({
        text: `${vi ? 'Mức tưới theo TCVN 8641' : 'Irrigation in TCVN 8641'}${scope}`,
        ref: { sourceId: 'tcvn8641', kind: 'standard', value: `${r.value[lang]} m³/ha`, label: `${name}${scope}` },
      });
    }
  } else {
    lines.push({
      text: vi ? 'TCVN 8641 không ghi mức tưới cho cây này.' : 'TCVN 8641 lists no irrigation amount for this crop.',
    });
  }
  lines.push({
    text: vi
      ? 'Một ô thử, một năm. Giá năm nay có thể khác; hỏi nơi thu mua ở xã.'
      : 'One plot, one year. Prices may differ this year; ask local buyers.',
  });
  return { type: 'crop', lines, evidence: [], kinds: ['study', 'standard'] };
}

function rankingAnswer(lang: Lang, f: Fmt, intro: string): Answer {
  const vi = lang === 'vi';
  const t = vi ? viText : en;
  const lines: AnswerLine[] = [{ text: intro }];
  for (const p of PLANS) {
    const total = planProfitMillion(p);
    const crops = p.textOnly ? p.textOnly.sequence[lang] : p.crops.map((c) => CROPS[c.crop].name[lang]).join(' → ');
    lines.push({
      text: `${planLabel(p, t.farmer)}: ${crops}`,
      ref:
        total !== null
          ? {
              sourceId: 'p02',
              kind: 'derived',
              value: `${f.n(total, 1)} ${t.common.millionPerHa}`,
              label: vi ? 'Lãi cả năm' : 'Yearly profit',
              chain: ['p02'],
            }
          : { sourceId: 'p03', kind: 'study', value: p.textOnly?.profitNote[lang] ?? '', label: vi ? 'Lãi' : 'Profit' },
    });
  }
  lines.push({
    text: vi
      ? 'Hãy so sánh trên các thẻ và bàn với cán bộ khuyến nông; quyết định là của gia đình bạn.'
      : 'Compare the cards and talk to the extension officer; the decision is your family’s.',
  });
  return { type: 'no-ranking', lines, evidence: [], kinds: ['study', 'derived'] };
}

/**
 * Answers only from evidence: a year look-up, a crop look-up, a refusal to rank, or the best-matching passages.
 * Returns an abstention when nothing matches well enough. It never produces a number that is not in the data.
 */
export function answer(question: string, lang: Lang, f: Fmt, text: { noEvidence: string; noRanking: string }): Answer {
  const q = normalize(question);
  if (!q) return { type: 'abstain', lines: [{ text: text.noEvidence }], evidence: [], kinds: [] };
  if (RANKING.test(q)) return rankingAnswer(lang, f, text.noRanking);
  if (FORECAST.test(q)) {
    const p = PASSAGES.find((x) => x.id === 'no-forecast');
    if (p)
      return {
        type: 'evidence',
        lines: passageLines(p, lang),
        evidence: [{ passage: p, score: 0, coverage: 1 }],
        kinds: [p.kind],
      };
  }
  const y = q.match(YEAR);
  if (y?.[1]) return yearAnswer(Number(y[1]), lang, f);
  const crop = CROP_WORDS.find(([re]) => re.test(q));
  const hits = search(question);
  const strong = hits.filter(isStrong);
  if (crop && (!strong[0] || strong[0].passage.id.startsWith('plan-') || /lai|loi|tien|profit|earn/.test(q)))
    return cropAnswer(crop[1], lang, f);
  if (!strong.length) return { type: 'abstain', lines: [{ text: text.noEvidence }], evidence: hits, kinds: [] };
  const top = strong.slice(0, 2);
  return {
    type: 'evidence',
    lines: top.flatMap((h) => passageLines(h.passage, lang)),
    evidence: top,
    kinds: [...new Set(top.map((h) => h.passage.kind))],
  };
}
