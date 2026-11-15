import { describe, expect, it } from 'vitest';

// H14, T14: React Router's ScrollRestoration and the viewTransition link prop write sessionStorage (hand-off item 8).
const sources = import.meta.glob<string>(['../**/*.{ts,tsx}', '!../**/*.test.{ts,tsx}'], {
  query: '?raw',
  import: 'default',
  eager: true,
});

const FORBIDDEN = [
  /\bviewTransition\b/,
  /\bScrollRestoration\b/,
  /\blocalStorage\b/,
  /\bsessionStorage\b/,
  /\bindexedDB\b/,
  /document\.cookie/,
];

describe('H14 no browser storage in the app code', () => {
  it('reads the app sources', () => {
    expect(Object.keys(sources).length).toBeGreaterThan(50);
  });

  it.each(FORBIDDEN.map((re) => [re.source, re] as const))('no file uses %s', (_, re) => {
    const hits = Object.entries(sources)
      .filter(([, code]) => code.split('\n').some((line) => re.test(line) && !/^\s*(\/\/|\/\*|\*)/.test(line)))
      .map(([file]) => file);
    expect(hits).toEqual([]);
  });
});

// D-167: only pictures with a recorded licence ship; the team's unlicensed mood photographs have no code path
describe('no unlicensed picture path', () => {
  it('no file reads the mood photographs', () => {
    expect(Object.entries(sources).filter(([, code]) => /media\.mood|HAS_MOOD|'mood'/.test(code))).toEqual([]);
  });
});
