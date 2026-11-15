import type { ReactNode } from 'react';
import type { SheetRef } from '../../domain/provenance';
import { useT } from '../../app/settings';
import { useProvenance } from './ProvenanceProvider';
import s from './SourceValue.module.css';

type Props = SheetRef & {
  children?: ReactNode;
  size?: 'md' | 'lg' | 'xl';
  /** Show the short source name under the value (officer mode). */
  showSource?: string;
};

/** A sourced number: the number itself is the button (H5). A dotted underline says "tap for the source". */
export function SourceValue(props: Props) {
  const { children, size = 'md', showSource } = props;
  const ref: SheetRef = props;
  const open = useProvenance();
  const t = useT();
  return (
    <button type="button" className={[s.val, s[size]].join(' ')} onClick={() => open(ref)} data-value={ref.value}>
      <span className={s.text}>
        <span className={s.figure}>{children ?? ref.value}</span>
        {showSource && <span className={s.src}>{showSource}</span>}
      </span>
      {/* the accessible name starts with the visible text, then says what it is and that it opens the source */}
      <span className="visually-hidden">{`, ${ref.label ? `${ref.label}: ` : ''}${ref.value}. ${t.common.source}`}</span>
    </button>
  );
}
