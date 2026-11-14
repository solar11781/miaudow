import { useState } from 'react';
import { api, ApiError, type SavedSet } from '../../api';
import { Button, ButtonLink } from '../../design-system/Button';
import { Confirm } from './Confirm';
import { NO_OWN, serializeFarmerState } from '../../domain/farmerState';
import { useApi } from '../../hooks/useApi';
import { useT } from '../../app/settings';
import { LoadState } from '../provenance/LoadState';
import { signInLink, useAccount, useSignInConfig } from './AccountProvider';
import s from './account.module.css';

const plansLink = (set: SavedSet) => ({
  pathname: '/nong-dan/phuong-an',
  search: `?${serializeFarmerState({ land: set.land, years: set.years, priority: set.priority, plan: null, own: NO_OWN }).toString()}`,
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
  const [error, setError] = useState<string | null>(null);

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
    <Confirm
      id="delete-all"
      label={t.account.deleteAll}
      leadingIcon="alert"
      question={t.account.deleteAllAsk}
      yes={t.account.deleteAllYes}
      no={t.account.deleteAllNo}
      onYes={remove}
      error={error}
    />
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
                <Confirm
                  id={`remove-${set.id}`}
                  label={t.account.remove}
                  ariaLabel={t.account.removeLabel(name(set))}
                  question={t.account.removeAsk}
                  yes={t.account.removeYes}
                  no={t.account.removeNo}
                  onYes={() => remove(set)}
                />
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

/** Signed out: the sign-in prompt while sign-in is on, otherwise only the line that it is not available. */
function SignedOut({ done, expired }: { done: string | null; expired: boolean }) {
  const t = useT();
  const [config, retry] = useSignInConfig();
  if (config.status !== 'ok') return <LoadState state={config} retry={retry} />;
  if (!config.data.available)
    return (
      <p className={s.note} role="status">
        {t.account.notAvailable}
      </p>
    );
  return (
    <>
      <p role="status">{done ?? (expired ? t.account.expired : t.account.needSignIn)}</p>
      <ButtonLink to={signInLink('/da-luu')} icon="arrowRight">
        {expired ? t.account.signInAgain : t.account.signInCta}
      </ButtonLink>
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
      {token ? <SavedList token={token} onDone={setDone} /> : <SignedOut done={done} expired={expired} />}
    </main>
  );
}
