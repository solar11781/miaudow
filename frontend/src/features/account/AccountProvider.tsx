import { createContext, useCallback, useContext, useMemo, useState, type ReactNode } from 'react';
import { ApiError } from '../../api';

interface Account {
  /** Google's ID token, kept in memory only (UI-UX-SPEC H14): never in the browser's storage, a cookie or an address. */
  token: string | null;
  /** True after the server answered 401 for the kept token, so a page can say "sign in again". */
  expired: boolean;
  signIn: (token: string) => void;
  signOut: () => void;
  /** Drops the token when an account call answered 401; passes every error on. */
  check: (err: unknown) => never;
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
  const value = useMemo(() => ({ token, expired, signIn, signOut, check }), [token, expired, signIn, signOut, check]);
  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}

export function useAccount() {
  const c = useContext(Ctx);
  if (!c) throw new Error('useAccount outside AccountProvider');
  return c;
}

// the pages a finished sign-in may return to; anything else goes to the saved answers page
const BACK = /^\/(nong-dan\/phuong-an|da-luu)(\?|$)/;
export const safeBack = (raw: string | null) => (raw && BACK.test(raw) ? raw : '/da-luu');

/** The sign-in route that comes back to `back` (a path with its answers) afterwards. */
export const signInLink = (back: string) => ({
  pathname: '/dang-nhap',
  search: `?${new URLSearchParams({ ve: back }).toString()}`,
});
