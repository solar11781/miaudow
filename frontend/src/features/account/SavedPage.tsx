import { useEffect, useRef, useState } from 'react';
import { api, ApiError, type SavedSet } from '../../api';
import { Button, ButtonLink } from '../../design-system/Button';
import { serializeFarmerState } from '../../domain/farmerState';
import { useApi } from '../../hooks/useApi';
import { useT } from '../../app/settings';
import { LoadState } from '../provenance/LoadState';
import { signInLink, useAccount } from './AccountProvider';
import s from './account.module.css';

const plansLink = (set: SavedSet) => ({
  pathname: '/nong-dan/phuong-an',
  search: `?${serializeFarmerState({ land: set.land, years: set.years, priority: set.priority, plan: null }).toString()}`,
});

/** The name of a saved set, from its answers; the server stores no name. */
function useSetName() {
  const t = useT();
  return (set: SavedSet) =>
    [
      t.farmer.lands[set.land].title,
      t.account.yearsLabel(set.years.join(', ')),
      t.farmer.prios[set.priority].title,
    ].join(' · ');
}

function errorText(t: ReturnType<typeof useT>, err: unknown) {
  return err instanceof ApiError && err.status === 503 ? t.account.unavailableNow : t.account.failed;
}

function DeleteAccount({ token, onDone }: { token: string; onDone: (message: string) => void }) {
  const t = useT();
  const { signOut, check } = useAccount();
  const [asking, setAsking] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const ask = useRef<HTMLParagraphElement>(null);
  const opener = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    if (asking) ask.current?.focus();
  }, [asking]);

  const remove = async () => {
    try {
      await api.account.deleteAccount(token).catch(check);
      signOut();
      onDone(t.account.deletedAll);
    } catch (err) {
      setError(errorText(t, err));
    }
  };

  return (
    <div className="stack">
      <Button
        ref={opener}
        variant="secondary"
        leadingIcon="alert"
        aria-expanded={asking}
        aria-controls="delete-all"
        onClick={() => setAsking(true)}
      >
        {t.account.deleteAll}
      </Button>
      {asking && (
        <div id="delete-all" className={s.confirm} role="group" aria-labelledby="delete-all-ask">
          <p id="delete-all-ask" ref={ask} tabIndex={-1}>
            <strong>{t.account.deleteAllAsk}</strong>
          </p>
          <div className="cluster">
            <Button onClick={remove}>{t.account.deleteAllYes}</Button>
            <Button
              variant="secondary"
              onClick={() => {
                setAsking(false);
                opener.current?.focus();
              }}
            >
              {t.account.deleteAllNo}
            </Button>
          </div>
          {error && <p role="alert">{error}</p>}
        </div>
      )}
    </div>
  );
}

function SavedList({ token, onDone }: { token: string; onDone: (message: string) => void }) {
  const t = useT();
  const name = useSetName();
  const { signOut, check } = useAccount();
  const [version, setVersion] = useState(0);
  const [sets, retry] = useApi((signal) => api.account.saved(token, signal).catch(check), `saved#${version}`);
  const [status, setStatus] = useState<string | null>(null);

  const remove = async (set: SavedSet) => {
    try {
      await api.account.remove(token, set.id).catch(check);
      setStatus(t.account.removed);
      setVersion((v) => v + 1);
    } catch (err) {
      setStatus(errorText(t, err));
    }
  };

  return (
    <>
      {sets.status !== 'ok' && <LoadState state={sets} retry={retry} />}
      {sets.status === 'ok' && sets.data.length === 0 && <p>{t.account.empty}</p>}
      {sets.status === 'ok' && sets.data.length > 0 && (
        <ul className={s.sets}>
          {sets.data.map((set) => (
            <li key={set.id} className={s.set}>
              <p>{name(set)}</p>
              <div className="cluster">
                <ButtonLink to={plansLink(set)} icon="arrowRight" aria-label={t.account.openLabel(name(set))}>
                  {t.account.open}
                </ButtonLink>
                <Button variant="secondary" aria-label={t.account.removeLabel(name(set))} onClick={() => remove(set)}>
                  {t.account.remove}
                </Button>
              </div>
            </li>
          ))}
        </ul>
      )}
      <p role="status">{status}</p>
      <div className={s.account}>
        <Button
          variant="ghost"
          onClick={() => {
            signOut();
            onDone(t.account.signedOut);
          }}
        >
          {t.account.signOut}
        </Button>
        <DeleteAccount token={token} onDone={onDone} />
      </div>
    </>
  );
}

/** /da-luu: the saved sets of answers of the signed-in farmer (UI-UX-SPEC §12c). */
export function SavedPage() {
  const t = useT();
  const { token, expired } = useAccount();
  const [done, setDone] = useState<string | null>(null);

  return (
    <main id="main" className={`container band-tight stack ${s.page}`}>
      <h1 className="h1" tabIndex={-1}>
        {t.account.savedTitle}
      </h1>
      <p className="lead">{t.account.savedLead}</p>
      {token ? (
        <SavedList token={token} onDone={setDone} />
      ) : (
        <>
          <p role="status">{done ?? (expired ? t.account.expired : t.account.needSignIn)}</p>
          <ButtonLink to={signInLink('/da-luu')} icon="arrowRight">
            {expired ? t.account.signInAgain : t.account.signInCta}
          </ButtonLink>
        </>
      )}
    </main>
  );
}
