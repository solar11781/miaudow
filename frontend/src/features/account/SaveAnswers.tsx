import { useState } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { api, ApiError, type SavedAnswers } from '../../api';
import { Button, ButtonLink } from '../../design-system/Button';
import { useApi } from '../../hooks/useApi';
import { useT } from '../../app/settings';
import { signInLink, useAccount } from './AccountProvider';
import s from './account.module.css';

type Status = 'idle' | 'saving' | 'saved' | 'full' | 'expired' | 'unavailable' | 'failed';

/** "Save these answers" on the plan cards, only while sign-in is on (UI-UX-SPEC §12c); signed out it leads to the
 * sign-in page, which comes back here with the same answers. */
export function SaveAnswers({ answers }: { answers: SavedAnswers }) {
  const t = useT();
  const { pathname, search } = useLocation();
  const { token, expired, check } = useAccount();
  const [config] = useApi(api.account.config, 'account-config');
  const [status, setStatus] = useState<Status>('idle');
  if (config.status !== 'ok' || !config.data.available) return null;

  const back = signInLink(`${pathname}${search}`);
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
        <Button variant="secondary" leadingIcon="check" disabled={status === 'saving'} onClick={() => save(token)}>
          {t.account.save}
        </Button>
      ) : (
        <ButtonLink to={back} variant="secondary" leadingIcon="check">
          {expired ? t.account.signInAgain : t.account.saveSignIn}
        </ButtonLink>
      )}
      <p role="status">
        {message}{' '}
        {(status === 'saved' || status === 'full') && (
          <Link to="/da-luu" className={s.link}>
            {t.account.goSaved}
          </Link>
        )}
      </p>
    </div>
  );
}
