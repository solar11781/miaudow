import type { Value } from '../../types';
import { SourceValue } from '../provenance/SourceValue';
import type { ApiRefs } from '../provenance/useApiRefs';
import { useT } from '../../app/settings';

/** A response value as its source button, or "not available" for a null value; `note` closes its source sheet.
 * `money` shows a money value in million dong per ha (D-190); its sheet keeps the exact value. */
export function NumberOr({
  v,
  label,
  refs,
  note,
  money,
}: {
  v: Value | null;
  label: string;
  refs: ApiRefs;
  note?: string;
  money?: boolean;
}) {
  const t = useT();
  if (!v) return <span className="muted">{t.common.notAvailable}</span>;
  const m = money ? refs.money(v) : null;
  return <SourceValue {...refs.value(v, label, note)}>{m && `${m.number} ${m.unit}`}</SourceValue>;
}
