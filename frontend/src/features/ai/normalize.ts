/** Lower-case, strip Vietnamese diacritics (đ → d) and punctuation, so “hạn hán”, “han han” and “HẠN” match. */
export function normalize(text: string): string {
  return text
    .normalize('NFD')
    .replace(/\p{M}/gu, '')
    .replace(/đ/g, 'd')
    .replace(/Đ/g, 'd')
    .toLowerCase()
    .replace(/[^a-z0-9\s]/g, ' ')
    .replace(/\s+/g, ' ')
    .trim();
}

/** True when the text carries Vietnamese diacritics; then words are matched with their accents kept. */
export const hasDiacritics = (text: string) => /[̀-ͯ]/.test(text.normalize('NFD')) || /[đĐ]/.test(text);

const keepAccents = (text: string) =>
  text
    .normalize('NFC')
    .toLowerCase()
    .replace(/[^\p{L}\p{N}\s]/gu, ' ')
    .replace(/\s+/g, ' ')
    .trim();

// Farmer words mapped to one key term, so questions in everyday language find the evidence. Matched on plain text.
const SYNONYMS: [RegExp, string][] = [
  [/\b(loi|lai|tien|thu nhap|lo lai|kiem duoc|profit|income|earn|money)\b/, 'k_lai'],
  [/\b(han|kho han|thieu nuoc|drought|dry|khong mua)\b/, 'k_han'],
  [/\b(nang suat|san luong|yield)\b/, 'k_nangsuat'],
  [/\b(nang nong|heat|hot)\b/, 'k_nong'],
  [/\b(ret|lanh|ret hai|cold)\b/, 'k_ret'],
  [/\b(mua lon|mua to|lu|ngap|heavy rain|flood)\b/, 'k_mualon'],
  [/\b(nuoc|tuoi|irrigation|water)\b/, 'k_nuoc'],
  [/\b(dat|do am|soil|nito|dam)\b/, 'k_dat'],
  [/\b(du doan|mo hinh|model|predict|prediction|hoc may|machine learning)\b/, 'k_mohinh'],
  [/\b(nasa|ve tinh|satellite|power|modis)\b/, 'k_nasa'],
  [/\b(nguon|source)\b/, 'k_nguon'],
  [/\b(lac|dau phong|peanut|groundnut)\b/, 'k_lac'],
  [/\b(ngo|bap|maize|corn)\b/, 'k_ngo'],
  [/\b(lua|thoc|rice|paddy)\b/, 'k_lua'],
];

const STOP = new Set([
  'da',
  'di',
  'nay',
  'roi',
  'se',
  'dang',
  'tu',
  'ra',
  'len',
  'thi',
  'ma',
  'vay',
  'sao',
  'la',
  'co',
  'khong',
  'cua',
  'va',
  'cho',
  'nha',
  'toi',
  'minh',
  'the',
  'nao',
  'bao',
  'nhieu',
  'gi',
  'o',
  'trong',
  'duoc',
  'nhu',
  'mot',
  'cac',
  'nhung',
  'voi',
  'a',
  'an',
  'is',
  'are',
  'what',
  'how',
  'of',
  'in',
  'to',
  'do',
  'does',
  'my',
  'i',
  'and',
  'for',
  'it',
  'be',
]);

/**
 * Search terms: the words (accents kept or stripped) plus the synonym key terms found in the text.
 * Stop words are judged on the plain form, so “đã” and “da” are both dropped.
 */
export function tokens(text: string, accented = false): string[] {
  const plain = normalize(text);
  const keys = SYNONYMS.filter(([re]) => re.test(plain)).map(([, k]) => k);
  const words = (accented ? keepAccents(text) : plain)
    .split(' ')
    .filter((w) => w.length > 1 && !STOP.has(normalize(w)));
  return [...words, ...keys];
}
