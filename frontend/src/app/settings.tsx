import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from 'react';
import { en } from '../i18n/en';
import { vi, type Messages } from '../i18n/vi';
import type { Bilingual } from '../domain/provenance';
import { useMedia } from '../hooks/useMedia';

export type Lang = 'vi' | 'en';
export type Theme = 'auto' | 'light' | 'dark';

interface Settings {
  lang: Lang;
  lite: boolean;
  theme: Theme;
  setLang: (l: Lang) => void;
  setLite: (v: boolean) => void;
  setTheme: (t: Theme) => void;
  /** True when motion should be avoided: lite mode or the system's reduced-motion setting. */
  calm: boolean;
}

const SettingsContext = createContext<Settings | null>(null);

/** Starting language from the browser (UI-UX-SPEC H16): Vietnamese when the browser lists Vietnamese, else English.
 * Nothing is stored in the browser (H14): settings live only in memory for this visit. */
export function browserLang(languages: readonly string[] | undefined): Lang {
  return (languages ?? []).some((l) => l.toLowerCase().startsWith('vi')) ? 'vi' : 'en';
}

export function SettingsProvider({ children }: { children: ReactNode }) {
  const [lang, setLang] = useState<Lang>(() =>
    typeof navigator === 'undefined'
      ? 'vi'
      : browserLang(navigator.languages?.length ? navigator.languages : [navigator.language]),
  );
  const [lite, setLite] = useState(false);
  const [theme, setTheme] = useState<Theme>('auto');
  const reduced = useMedia('(prefers-reduced-motion: reduce)');
  // D-187: Auto follows the phone's light or dark setting; dark stays the default when the phone does not say light
  const systemLight = useMedia('(prefers-color-scheme: light)');

  useEffect(() => {
    const root = document.documentElement;
    root.lang = lang;
    root.dataset.lite = String(lite);
    root.dataset.theme = theme === 'auto' ? (systemLight ? 'light' : 'dark') : theme;
    document.title = (lang === 'vi' ? vi : en).meta.title;
  }, [lang, lite, theme, systemLight]);

  const value = useMemo<Settings>(
    () => ({ lang, lite, theme, setLang, setLite, setTheme, calm: lite || reduced }),
    [lang, lite, theme, reduced],
  );
  return <SettingsContext.Provider value={value}>{children}</SettingsContext.Provider>;
}

export function useSettings(): Settings {
  const s = useContext(SettingsContext);
  if (!s) throw new Error('useSettings outside SettingsProvider');
  return s;
}

/** Messages of the current language. */
export function useT(): Messages {
  return useSettings().lang === 'vi' ? vi : en;
}

/** Picks the current language from a bilingual value. */
export function usePick() {
  const { lang } = useSettings();
  return useCallback((b: Bilingual) => b[lang], [lang]);
}

/** Locale-aware number formatting (Vietnamese uses a decimal comma and a dot for thousands). */
export function useFormat() {
  const { lang } = useSettings();
  return useMemo(() => {
    const locale = lang === 'vi' ? 'vi-VN' : 'en-GB';
    const n = (v: number, digits = 0) =>
      new Intl.NumberFormat(locale, { maximumFractionDigits: digits, minimumFractionDigits: digits }).format(v);
    return {
      n,
      pct: (share: number, digits = 0) => `${n(share * 100, digits)}%`,
      signedPct: (share: number, digits = 1) =>
        `${share > 0 ? '+' : share < 0 ? '−' : ''}${n(Math.abs(share) * 100, digits)}%`,
      million: (thousands: number) => n(thousands / 1000, 1),
    };
  }, [lang]);
}
