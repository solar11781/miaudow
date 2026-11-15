import { createContext, useCallback, useContext, useMemo, useRef, useState, type ReactNode } from 'react';
import { api, ApiError } from '../../api';
import { useApi } from '../../hooks/useApi';

interface Account {
  /** Google's ID token, kept in memory only (UI-UX-SPEC H14): never in the browser's storage, a cookie or an address. */
  token: string | null;
  /** True after the server answered 401 for the kept token, so a page can say "sign in again". */
  expired: boolean;
  signIn: (token: string) => void;
  signOut: () => void;
  /** Drops the token when an account call answered 401; passes every error on. */
  check: (err: unknown) => never;
  /** Keeps `full` (the way back with the typed prices and costs) in memory while the sign-in page has only `back`. */
  hold: (back: string, full: string) => void;
  /** Where a finished sign-in to `back` goes: the held way back when it was held for `back`, otherwise `back`. */
  returnTo: (back: string) => string;
}

const Ctx = createContext<Account | null>(null);

export function AccountProvider({ children }: { children: ReactNode }) {
  const [token, setToken] = useState<string | null>(null);
  const [expired, setExpired] = useState(false);
  const signIn = useCallback((t: string) => {
    setToken(t);
    setExpired(false);
  }, []);
  const signOut = useCallback(() => {
    setToken(null);
    setExpired(false);
    window.google?.accounts.id.disableAutoSelect();
  }, []);
  const check = useCallback((err: unknown): never => {
    if (err instanceof ApiError && err.status === 401) {
      setToken(null);
      setExpired(true);
    }
    throw err;
  }, []);
  // D-180: Google's script runs on the sign-in page and can read its address, so the typed numbers wait here, never
  // in the browser's storage (H14), and the hash router's in-app trip keeps this memory
  const held = useRef<{ back: string; full: string } | null>(null);
  const hold = useCallback((back: string, full: string) => {
    held.current = { back, full };
  }, []);
  const returnTo = useCallback((back: string) => {
    const found = held.current;
    held.current = null;
    return found?.back === back ? found.full : back;
  }, []);
  const value = useMemo(
    () => ({ token, expired, signIn, signOut, check, hold, returnTo }),
    [token, expired, signIn, signOut, check, hold, returnTo],
  );
  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}

export function useAccount() {
  const c = useContext(Ctx);
  if (!c) throw new Error('useAccount outside AccountProvider');
  return c;
}

/** The sign-in config, read once per page. */
export const useSignInConfig = () => useApi(api.account.config, 'account-config');

/** True once the server said sign-in is on; false while loading, off or unreachable. */
export function useSignInAvailable() {
  const [config] = useSignInConfig();
  return config.status === 'ok' && config.data.available;
}

// the pages a finished sign-in may return to; anything else goes to the saved answers page
const BACK = /^\/(nong-dan\/phuong-an|da-luu|farmer\/plans|saved)(\?|$)/; // both path languages (D-174)
export const safeBack = (raw: string | null) => (raw && BACK.test(raw) ? raw : '/da-luu');

/** The sign-in route that comes back to `back` (a path with its answers) afterwards. */
export const signInLink = (back: string) => ({
  pathname: '/dang-nhap',
  search: `?${new URLSearchParams({ ve: back }).toString()}`,
});
