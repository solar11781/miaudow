import type { Value } from '../../types';
import { SourceValue } from '../provenance/SourceValue';
import type { ApiRefs } from '../provenance/useApiRefs';
import { useT } from '../../app/settings';

/** A response value as its source button, or "not available" for a null value; `note` closes its source sheet and
 * `plain` says the value in plain words under its number (D-192).
 * `money` shows a money value in million dong per ha (D-190); its sheet keeps the exact value. */
export function NumberOr({
  v,
  label,
  refs,
  note,
  plain,
  money,
}: {
  v: Value | null;
  label: string;
  refs: ApiRefs;
  note?: string;
  plain?: string;
  money?: boolean;
}) {
  const t = useT();
  if (!v) return <span className="muted">{t.common.notAvailable}</span>;
  const m = money ? refs.money(v) : null;
  return (
    <SourceValue {...(money ? refs.moneyValue(v, label, note) : refs.value(v, label, note))} plain={plain}>
      {m && `${m.number} ${m.unit}`}
    </SourceValue>
  );
}
