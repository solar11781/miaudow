import { useEffect, useRef, useState } from 'react';
import { Link, useLocation, useSearchParams } from 'react-router-dom';
import { api, ApiError, type SavedAnswers } from '../../api';
import { Button, ButtonLink } from '../../design-system/Button';
import { useT } from '../../app/settings';
import { useLocalTo } from '../../app/paths';
import { signInLink, useAccount, useSignInAvailable } from './AccountProvider';
import { isOwnKey } from '../../domain/farmerState';
import s from './account.module.css';

type Status = 'idle' | 'saving' | 'saved' | 'full' | 'expired' | 'unavailable' | 'failed';
// marks a save the farmer asked for before signing in; the sign-in page returns with it, and it is dropped at once
const PENDING = 'luu';

/** "Save these answers" on the plan cards, only while sign-in is on (UI-UX-SPEC §12c); signed out it leads to the
 * sign-in page, which comes back here with the same answers and saves them. */
export function SaveAnswers({ answers }: { answers: SavedAnswers }) {
  const t = useT();
  const { pathname, search } = useLocation();
  const [params, setParams] = useSearchParams();
  const { token, expired, check, hold, release } = useAccount();
  const available = useSignInAvailable();
  const [status, setStatus] = useState<Status>('idle');
  const started = useRef(false);
  const local = useLocalTo();
  // back on the plan cards, a way back held for an earlier tap is stale: the farmer may change the numbers here
  useEffect(() => release(), [release]);

  const save = async (signedIn: string) => {
    setStatus('saving');
    try {
      await api.account.save(signedIn, answers).catch(check);
      setStatus('saved');
    } catch (err) {
      const code = err instanceof ApiError ? err.status : 0;
      setStatus(code === 409 ? 'full' : code === 401 ? 'expired' : code === 503 ? 'unavailable' : 'failed');
    }
  };

  const pending = params.get(PENDING) === '1';
  useEffect(() => {
    if (!pending || !token || !available || started.current) return;
    started.current = true;
    setParams(
      (p) => {
        p.delete(PENDING);
        return p;
      },
      { replace: true, preventScrollReset: true },
    );
    void save(token);
    // runs once, when the farmer is back from signing in with a pending save
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [pending, token, available]);

  if (!available) return null;

  const again = new URLSearchParams(search);
  again.set(PENDING, '1');
  const full = `${pathname}?${again.toString()}`;
  // Google's script runs on the sign-in page and can read its address, so the typed price and costs stay out of it
  // and wait in memory for the way back (D-180)
  for (const key of [...again.keys()]) if (isOwnKey(key)) again.delete(key);
  const back = `${pathname}?${again.toString()}`;
  const message = {
    idle: null,
    saving: t.account.saving,
    saved: t.account.saved,
    full: t.account.full,
    expired: t.account.expired,
    unavailable: t.account.unavailableNow,
    failed: t.account.failed,
  }[status];

  return (
    <div className={s.save}>
      {token ? (
        // once saved, the same answers cannot be stored twice; new answers mount a new control (PlansStep key)
        <Button
          variant="secondary"
          leadingIcon="check"
          disabled={status === 'saving' || status === 'saved'}
          onClick={() => save(token)}
        >
          {status === 'saved' ? t.account.savedDone : t.account.save}
        </Button>
      ) : (
        <ButtonLink to={signInLink(back)} onClick={() => hold(back, full)} variant="secondary" leadingIcon="check">
          {expired ? t.account.signInAgain : t.account.saveSignIn}
        </ButtonLink>
      )}
      <p role="status">
        {message}{' '}
        {(status === 'saved' || status === 'full') && (
          <Link to={local('/da-luu')} className={s.link}>
            {t.account.goSaved}
          </Link>
        )}
      </p>
    </div>
  );
}
