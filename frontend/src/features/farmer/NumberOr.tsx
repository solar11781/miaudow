import type { Value } from '../../types';
import { SourceValue } from '../provenance/SourceValue';
import type { ApiRefs } from '../provenance/useApiRefs';
import { useT } from '../../app/settings';

/** A response value as its source button, or "not available" for a null value. */
export function NumberOr({ v, label, refs }: { v: Value | null; label: string; refs: ApiRefs }) {
  const t = useT();
  return v ? <SourceValue {...refs.value(v, label)} /> : <span className="muted">{t.common.notAvailable}</span>;
}
