import { createContext, useCallback, useContext, useEffect, useRef, useState, type ReactNode } from 'react';
import type { SourceRef } from '../../domain/provenance';
import { ProvenanceSheet } from './ProvenanceSheet';

const Ctx = createContext<((ref: SourceRef) => void) | null>(null);

/** One shared sheet for the whole app; any sourced number opens it with its own reference. */
export function ProvenanceProvider({ children }: { children: ReactNode }) {
  const [current, setCurrent] = useState<SourceRef | null>(null);
  const dialog = useRef<HTMLDialogElement>(null);

  const open = useCallback((ref: SourceRef) => setCurrent(ref), []);

  useEffect(() => {
    const d = dialog.current;
    if (!d) return;
    if (current && !d.open) d.showModal();
    if (!current && d.open) d.close();
  }, [current]);

  return (
    <Ctx.Provider value={open}>
      {children}
      <ProvenanceSheet ref={dialog} value={current} onClose={() => setCurrent(null)} />
    </Ctx.Provider>
  );
}

export function useProvenance() {
  const open = useContext(Ctx);
  if (!open) throw new Error('useProvenance outside ProvenanceProvider');
  return open;
}
