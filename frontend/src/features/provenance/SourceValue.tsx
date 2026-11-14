import type { ReactNode } from 'react';
import type { SourceRef } from '../../domain/provenance';
import { SealGlyph } from '../../design-system/Icon';
import { useT } from '../../app/settings';
import { useProvenance } from './ProvenanceProvider';
import s from './SourceValue.module.css';

interface Props extends SourceRef {
  children?: ReactNode;
  size?: 'md' | 'lg' | 'xl';
  /** Show the short source name under the value (officer mode). */
  showSource?: string;
}

/** A sourced number: the number itself is the button, and the red seal says "tap for the source". */
export function SourceValue({ children, size = 'md', showSource, ...ref }: Props) {
  const open = useProvenance();
  const t = useT();
  return (
    <button
      type="button"
      className={[s.val, s[size]].join(' ')}
      onClick={() => open(ref)}
      data-value={ref.value}
    >
      <span className={s.text}>
        <span className={s.figure}>{children ?? ref.value}</span>
        {showSource && <span className={s.src}>{showSource}</span>}
      </span>
      {/* the accessible name starts with the visible text, then says what it is and that it opens the source */}
      <span className="visually-hidden">{`, ${ref.label ? `${ref.label}: ` : ''}${ref.value}. ${t.common.source}`}</span>
      <span className={s.seal} aria-hidden="true"><SealGlyph /></span>
    </button>
  );
}
