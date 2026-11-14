import { DATASETS, type IngestionStatus } from '../../data/catalog';
import { Icon } from '../../design-system/Icon';
import { Reveal } from '../../design-system/Reveal';
import { usePick, useT } from '../../app/settings';
import s from './evidence.module.css';

const ORDER: IngestionStatus[] = ['INGESTED', 'PARTIAL', 'CONTRACT_ONLY', 'BLOCKED'];

/** Every dataset with its real ingestion state: what is loaded, what is only a contract, what is blocked. */
export function Datasets() {
  const t = useT();
  const pick = usePick();
  const rows = [...DATASETS].sort((a, b) => ORDER.indexOf(a.ingestion_status) - ORDER.indexOf(b.ingestion_status));
  return (
    <section className="band surface-paper" aria-labelledby="ev-data">
      <div className="container stack" style={{ ['--gap' as string]: 'var(--s-6)' }}>
        <Reveal className={s.sectionHead}>
          <h2 id="ev-data" className="h1">
            {t.evidence.dataTitle}
          </h2>
          <p className="lead">{t.evidence.dataLead}</p>
        </Reveal>
        <ul className={s.datasets}>
          {rows.map((d) => (
            <li key={d.dataset_id} className={s.dataset} data-state={d.ingestion_status}>
              <div className={s.datasetHead}>
                <Icon name="database" size={20} />
                <h3 className={s.datasetTitle}>{pick(d.title)}</h3>
                <span className={s.ingest} data-state={d.ingestion_status}>
                  {t.evidence.ingestion[d.ingestion_status]}
                </span>
              </div>
              <dl className={s.facts}>
                <dt>{t.evidence.provider}</dt>
                <dd>{d.provider}</dd>
                <dt>{t.evidence.resolution}</dt>
                <dd>{d.spatial_resolution}</dd>
                <dt>{t.evidence.coverage}</dt>
                <dd>{d.temporal_coverage}</dd>
                <dt>{t.evidence.licence}</dt>
                <dd>{d.license}</dd>
                <dt>{t.evidence.fieldMeasured}</dt>
                <dd>{d.is_field_measurement ? t.evidence.yes : t.evidence.no}</dd>
              </dl>
              {/* a blocked dataset's note counts CMR granules from a query that was not recorded, so it is not shown (D-169) */}
              {d.notes.length > 0 && d.ingestion_status !== 'BLOCKED' && (
                <p className={s.dsNote}>{pick(d.notes[0] as { vi: string; en: string })}</p>
              )}
            </li>
          ))}
        </ul>
      </div>
    </section>
  );
}
