import { useCallback, useEffect, useState } from 'react';

export type Loaded<T> = { status: 'loading' } | { status: 'error' } | { status: 'ok'; data: T };

const LOADING = { status: 'loading' } as const;

/** Loads one API response for a screen; `key` names the request, so a new key loads again. Nothing is cached in the
 * browser's storage (H14). */
export function useApi<T>(load: (signal: AbortSignal) => Promise<T>, key: string): [Loaded<T>, () => void] {
  const [attempt, setAttempt] = useState(0);
  const id = `${key}#${attempt}`;
  const [done, setDone] = useState<{ id: string; result: Loaded<T> } | null>(null);
  useEffect(() => {
    const ctrl = new AbortController();
    load(ctrl.signal).then(
      (data) => {
        if (!ctrl.signal.aborted) setDone({ id, result: { status: 'ok', data } });
      },
      () => {
        if (!ctrl.signal.aborted) setDone({ id, result: { status: 'error' } });
      },
    );
    return () => ctrl.abort();
    // the request is named by id; load is a new closure on every render
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id]);
  const retry = useCallback(() => setAttempt((a) => a + 1), []);
  return [done?.id === id ? done.result : LOADING, retry];
}
