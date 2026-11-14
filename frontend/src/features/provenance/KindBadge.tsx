import type { EvidenceKind } from '../../domain/provenance';
import { useT } from '../../app/settings';
import s from './KindBadge.module.css';

/** Names the kind of evidence in words and colour (never colour alone). */
export function KindBadge({ kind, compact }: { kind: EvidenceKind; compact?: boolean }) {
  const t = useT();
  return (
    <span
      className={[s.badge, compact ? s.compact : ''].join(' ')}
      style={{ ['--k' as string]: `var(--kind-${kind})` }}
      title={t.kindHelp[kind]}
    >
      <span className={s.dot} aria-hidden="true" />
      {t.kinds[kind]}
    </span>
  );
}
