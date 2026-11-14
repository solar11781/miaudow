import { dataNames } from '../../domain/dataLine';
import type { SourceFacts } from '../../types';
import { useT } from '../../app/settings';

/** "Data: ..." naming only the datasets the loaded response cites (H19, D-169). */
export function DataLine({ sources, className }: { sources: Record<string, SourceFacts>; className?: string }) {
  const t = useT();
  return <p className={className}>{t.farmer.dataLine(dataNames(sources, t.farmer.dataSources).join(' · '))}</p>;
}
