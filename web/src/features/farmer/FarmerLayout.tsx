import { createContext, useCallback, useContext, useEffect, useMemo, type ReactNode } from 'react';
import { Link, Outlet, useLocation, useSearchParams } from 'react-router-dom';
import { parseFarmerState, serializeFarmerState, type FarmerState } from '../../domain/farmerState';
import { Icon } from '../../design-system/Icon';
import { useT } from '../../app/settings';
import s from './farmer.module.css';

const STORE = 'miaudow.farmer.v1';
export const STEP_PATHS = ['/nong-dan/ruong', '/nong-dan/nam', '/nong-dan/uu-tien', '/nong-dan/phuong-an'] as const;

interface FarmerCtx {
  state: FarmerState;
  update: (patch: Partial<FarmerState>) => void;
  /** The current search string, so links between steps keep the answers. */
  search: string;
}

const Ctx = createContext<FarmerCtx | null>(null);

export function useFarmer() {
  const c = useContext(Ctx);
  if (!c) throw new Error('useFarmer outside FarmerLayout');
  return c;
}

/** Holds the farmer's answers in the URL (shareable, survives reload) and mirrors them to local storage. */
export function FarmerLayout() {
  const [params, setParams] = useSearchParams();
  const state = useMemo(() => parseFarmerState(params), [params]);

  useEffect(() => {
    if ([...params.keys()].length) return;
    try {
      const saved = window.localStorage.getItem(STORE);
      if (saved) setParams(new URLSearchParams(saved), { replace: true });
    } catch { /* storage blocked: start fresh */ }
  }, [params, setParams]);

  useEffect(() => {
    try { window.localStorage.setItem(STORE, serializeFarmerState(state).toString()); } catch { /* ignore */ }
  }, [state]);

  const update = useCallback(
    (patch: Partial<FarmerState>) => setParams(serializeFarmerState({ ...state, ...patch }), { replace: true, preventScrollReset: true }),
    [state, setParams],
  );
  const search = `?${serializeFarmerState(state).toString()}`;
  const value = useMemo(() => ({ state, update, search }), [state, update, search]);

  return (
    <Ctx.Provider value={value}>
      <main id="main" className={`surface-paper ${s.page}`}>
        <Outlet />
      </main>
    </Ctx.Provider>
  );
}

/** Back link, step progress and the page title of one step. */
export function StepShell({ step, title, help, children, actions, wide }: {
  step: 1 | 2 | 3 | 4; title: string; help?: string; children: ReactNode; actions?: ReactNode; wide?: boolean;
}) {
  const t = useT();
  const { search } = useFarmer();
  const { pathname } = useLocation();
  const prev = step === 1 ? '/nong-dan' : STEP_PATHS[step - 2];
  return (
    <div className={[s.shell, wide ? s.wide : ''].join(' ')}>
      <div className={s.top}>
        <Link to={{ pathname: prev, search }} className={s.back} viewTransition>
          <Icon name="arrowLeft" size={20} /> {t.common.back}
        </Link>
        <ol className={s.progress} aria-label={t.farmer.stepOf(step)}>
          {STEP_PATHS.map((p, i) => (
            <li key={p} aria-current={pathname === p ? 'step' : undefined} className={i < step ? s.done : ''}>
              <span className="visually-hidden">{t.farmer.stepOf(i + 1)}</span>
            </li>
          ))}
        </ol>
        <span className={s.stepLabel} aria-hidden="true">{t.farmer.stepOf(step)}</span>
      </div>
      <header className={s.head}>
        <h1 className={`h1 ${s.title}`}>{title}</h1>
        {help && <p className="lead">{help}</p>}
      </header>
      {children}
      {actions && <div className={s.actions}>{actions}</div>}
    </div>
  );
}
