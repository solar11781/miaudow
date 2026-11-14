import { useEffect, useEffectEvent, useRef, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { api, ApiError } from '../../api';
import { Button, ButtonLink } from '../../design-system/Button';
import { useApi } from '../../hooks/useApi';
import { useSettings, useT } from '../../app/settings';
import { LoadState } from '../provenance/LoadState';
import { safeBack, useAccount } from './AccountProvider';
import { loadGoogle } from './google';
import s from './account.module.css';

/** Google's own button; Google's script is added only when this mounts, after the notice was read. */
function GoogleButton({ clientId, onToken }: { clientId: string; onToken: (credential: string) => void }) {
  const t = useT();
  const { lang } = useSettings();
  const box = useRef<HTMLDivElement>(null);
  const [state, setState] = useState<'loading' | 'ready' | 'failed'>('loading');
  const [attempt, setAttempt] = useState(0);
  const token = useEffectEvent(onToken);

  useEffect(() => {
    let live = true;
    loadGoogle().then(
      (id) => {
        const el = box.current;
        if (!live || !el) return;
        id.initialize({ client_id: clientId, callback: (answer) => token(answer.credential) });
        el.replaceChildren();
        id.renderButton(el, {
          type: 'standard',
          theme: 'outline',
          size: 'large',
          text: 'signin_with',
          shape: 'pill',
          locale: lang,
        });
        setState('ready');
      },
      () => {
        if (live) setState('failed');
      },
    );
    return () => {
      live = false;
    };
  }, [clientId, lang, attempt]);

  return (
    <div className="stack">
      {state === 'loading' && <p role="status">{t.account.googleLoading}</p>}
      {state === 'ready' && <p>{t.account.googleHelp}</p>}
      {state === 'failed' && (
        <div className="stack" role="alert">
          <p>{t.account.googleFailed}</p>
          <Button
            variant="secondary"
            onClick={() => {
              setState('loading');
              setAttempt((a) => a + 1);
            }}
          >
            {t.common.retry}
          </Button>
        </div>
      )}
      <div ref={box} className={s.google} data-testid="google-button" />
    </div>
  );
}

function Notice() {
  const t = useT();
  return (
    <section className={s.notice} aria-labelledby="sign-in-notice">
      <h2 id="sign-in-notice" className="h3">
        {t.account.noticeTitle}
      </h2>
      <ul className="stack">
        {t.account.notice.map((line) => (
          <li key={line}>{line}</li>
        ))}
      </ul>
      {/* the full notice is the server page at the address registered with Google (D-164) */}
      <a href="/quyen-rieng-tu" className={s.link}>
        {t.account.noticeFull}
      </a>
    </section>
  );
}

type Step = 'notice' | 'google' | 'busy' | 'failed' | 'unavailable';

/** /dang-nhap: the optional Google sign-in (UI-UX-SPEC §12c), the privacy notice first. */
export function SignInPage() {
  const t = useT();
  const [params] = useSearchParams();
  const back = safeBack(params.get('ve'));
  const navigate = useNavigate();
  const { token, signIn } = useAccount();
  const [config, retry] = useApi(api.account.config, 'account-config');
  const [step, setStep] = useState<Step>('notice');

  const onToken = async (credential: string) => {
    setStep('busy');
    try {
      await api.account.signIn(credential);
      signIn(credential);
      navigate(back);
    } catch (err) {
      setStep(err instanceof ApiError && err.status === 503 ? 'unavailable' : 'failed');
    }
  };

  let body;
  if (config.status !== 'ok') body = <LoadState state={config} retry={retry} />;
  else if (!config.data.available || step === 'unavailable')
    body = (
      <p className={s.note} role="status">
        {t.account.notAvailable}
      </p>
    );
  else if (token)
    body = (
      <>
        <p role="status">{t.account.signedIn}</p>
        <ButtonLink to={back} icon="arrowRight">
          {t.account.continue}
        </ButtonLink>
      </>
    );
  else
    body = (
      <>
        <Notice />
        {step === 'notice' ? (
          <Button onClick={() => setStep('google')} icon="arrowRight">
            {t.account.agree}
          </Button>
        ) : (
          <GoogleButton clientId={config.data.client_id} onToken={onToken} />
        )}
        {step === 'busy' && <p role="status">{t.account.signingIn}</p>}
        {step === 'failed' && (
          <p className={s.note} role="alert">
            {t.account.signInFailed}
          </p>
        )}
      </>
    );

  return (
    <main id="main" className={`container band-tight stack ${s.page}`}>
      <h1 className="h1" tabIndex={-1}>
        {t.account.signInTitle}
      </h1>
      <p className="lead">{t.account.signInLead}</p>
      {body}
    </main>
  );
}
