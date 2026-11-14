import { Button } from '../../design-system/Button';
import type { Loaded } from '../../hooks/useApi';
import { useT } from '../../app/settings';
import s from './LoadState.module.css';

/** Grey placeholder blocks while loading, or the error line with a retry button (UI-UX-SPEC section 11). */
export function LoadState({ state, retry }: { state: Loaded<unknown>; retry: () => void }) {
  const t = useT();
  if (state.status === 'error') {
    return (
      <div className={s.error} role="alert">
        <p>{t.common.error}</p>
        <Button variant="secondary" onClick={retry}>{t.common.retry}</Button>
      </div>
    );
  }
  return (
    <div className={s.blocks} aria-busy="true">
      <span className="visually-hidden">{t.common.loading}</span>
      <i /><i /><i />
    </div>
  );
}
