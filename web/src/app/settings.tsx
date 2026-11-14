import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from 'react';
import { en } from '../i18n/en';
import { vi, type Messages } from '../i18n/vi';
import type { Bilingual } from '../domain/provenance';

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

const KEY = 'miaudow.settings.v1';
const SettingsContext = createContext<Settings | null>(null);

function readStored(): Partial<Pick<Settings, 'lang' | 'lite' | 'theme'>> {
  try {
    const raw = window.localStorage.getItem(KEY);
    return raw ? (JSON.parse(raw) as Partial<Settings>) : {};
  } catch {
    return {};
  }
}

const prefersReducedMotion = () =>
  typeof window !== 'undefined' && window.matchMedia?.('(prefers-reduced-motion: reduce)').matches === true;

export function SettingsProvider({ children }: { children: ReactNode }) {
  const [stored] = useState(readStored);
  const [lang, setLang] = useState<Lang>(stored.lang === 'en' ? 'en' : 'vi');
  const [lite, setLite] = useState<boolean>(stored.lite === true);
  const [theme, setTheme] = useState<Theme>(stored.theme ?? 'auto');
  const [reduced, setReduced] = useState(prefersReducedMotion);

  useEffect(() => {
    const mq = window.matchMedia?.('(prefers-reduced-motion: reduce)');
    if (!mq) return;
    const on = () => setReduced(mq.matches);
    mq.addEventListener('change', on);
    return () => mq.removeEventListener('change', on);
  }, []);

  useEffect(() => {
    try {
      window.localStorage.setItem(KEY, JSON.stringify({ lang, lite, theme }));
    } catch {
      /* storage blocked: the page still works, settings just are not remembered */
    }
    const root = document.documentElement;
    root.lang = lang;
    root.dataset.lite = String(lite);
    if (theme === 'auto') delete root.dataset.theme;
    else root.dataset.theme = theme;
    document.title = (lang === 'vi' ? vi : en).meta.title;
  }, [lang, lite, theme]);

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
    const n = (v: number, digits = 0) => new Intl.NumberFormat(locale, { maximumFractionDigits: digits, minimumFractionDigits: digits }).format(v);
    return {
      n,
      pct: (share: number, digits = 0) => `${n(share * 100, digits)}%`,
      signedPct: (share: number, digits = 1) => `${share > 0 ? '+' : share < 0 ? '−' : ''}${n(Math.abs(share) * 100, digits)}%`,
      million: (thousands: number) => n(thousands / 1000, 1),
    };
  }, [lang]);
}
