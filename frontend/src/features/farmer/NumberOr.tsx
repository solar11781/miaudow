import type { Value } from '../../types';
import { SourceValue } from '../provenance/SourceValue';
import type { ApiRefs } from '../provenance/useApiRefs';
import { useT } from '../../app/settings';

/** A response value as its source button, or "not available" for a null value; `note` closes its source sheet. */
export function NumberOr({ v, label, refs, note }: { v: Value | null; label: string; refs: ApiRefs; note?: string }) {
  const t = useT();
  return v ? <SourceValue {...refs.value(v, label, note)} /> : <span className="muted">{t.common.notAvailable}</span>;
}
