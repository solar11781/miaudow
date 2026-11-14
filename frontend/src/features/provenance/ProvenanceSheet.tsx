import { forwardRef } from 'react';
import { SOURCES } from '../../domain/sources';
import type { ApiSourceRef, SheetRef } from '../../domain/provenance';
import type { SourceFacts } from '../../types';
import { Icon } from '../../design-system/Icon';
import { KindBadge } from './KindBadge';
import { readStatusText } from './readStatus';
import { usePick, useT } from '../../app/settings';
import s from './ProvenanceSheet.module.css';

interface Props {
  value: SheetRef | null;
  onClose: () => void;
}

export const ProvenanceSheet = forwardRef<HTMLDialogElement, Props>(function ProvenanceSheet({ value, onClose }, ref) {
  const t = useT();
  const pick = usePick();
  const src = value && 'sourceId' in value ? SOURCES[value.sourceId] : null;
  return (
    <dialog
      ref={ref}
      className={s.sheet}
      aria-labelledby="prov-title"
      onClose={onClose}
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
    >
      {value && 'facts' in value && <ApiSheet value={value} onClose={onClose} />}
      {value && src && 'kind' in value && (
        <div className={s.inner}>
          <div className={s.grab} aria-hidden="true" />
          <header className={s.head}>
            <span className={s.stamp} aria-hidden="true">
              {t.common.source}
            </span>
            <div className={s.headText}>
              <p className={s.label}>{value.label || t.sheet.aboutValue}</p>
              <h2 id="prov-title" className={s.value}>
                {value.value}
              </h2>
              <KindBadge kind={value.kind} />
              <p className={s.kindHelp}>{t.kindHelp[value.kind]}</p>
            </div>
            <button type="button" className={s.close} onClick={onClose} aria-label={t.common.close}>
              <Icon name="close" />
            </button>
          </header>

          {value.detail && (
            <section className={s.arith}>
              <h3>{t.sheet.arithmetic}</h3>
              <p>{value.detail}</p>
            </section>
          )}

          {value.chain && value.chain.length > 0 && (
            <section>
              <h3 className={s.h3}>{t.sheet.chain}</h3>
              <ol className={s.chain}>
                {value.chain.map((id) => (
                  <li key={id}>
                    <KindBadge kind={SOURCES[id].kind} compact /> <span>{SOURCES[id].short}</span>
                  </li>
                ))}
              </ol>
            </section>
          )}

          <dl className={s.facts}>
            <dt>{t.sheet.from}</dt>
            <dd>{pick(src.title)}</dd>
            <dt>{t.sheet.registerId}</dt>
            <dd className="mono">{src.registerId}</dd>
            <dt>{t.sheet.publisher}</dt>
            <dd>{pick(src.publisher)}</dd>
            <dt>{t.sheet.where}</dt>
            <dd>{pick(src.where)}</dd>
            <dt>{t.sheet.period}</dt>
            <dd>{pick(src.period)}</dd>
            <dt>{t.sheet.method}</dt>
            <dd>{pick(src.method)}</dd>
            <dt>{t.sheet.howRead}</dt>
            <dd>{pick(src.howRead)}</dd>
            {src.licence && (
              <>
                <dt>{t.sheet.licence}</dt>
                <dd>{pick(src.licence)}</dd>
              </>
            )}
          </dl>

          <p className={s.caveat}>
            <strong>{t.sheet.caveat}:</strong> {pick(src.caveat)}
          </p>

          {src.url && (
            <a className={s.link} href={src.url} target="_blank" rel="noreferrer noopener">
              {t.sheet.link} <Icon name="arrowUpRight" size={16} />
            </a>
          )}
        </div>
      )}
    </dialog>
  );
});

/** One block per source of an API value, rows in the order of UI-UX-SPEC section 10, facts from the response only. */
function FactsBlock({ facts }: { facts: SourceFacts }) {
  const t = useT();
  const pick = usePick();
  return (
    <section className={s.block}>
      <dl className={s.facts}>
        <dt>{t.sheet.name}</dt>
        <dd>{pick(facts.citation)}</dd>
        <dt>{t.sheet.type}</dt>
        <dd>{pick(facts.study_type)}</dd>
        <dt>{t.sheet.placeYears}</dt>
        <dd>{pick(facts.place_years)}</dd>
        {facts.read_status !== null && (
          <>
            <dt>{t.sheet.readStatus}</dt>
            <dd>{readStatusText(facts.read_status, t.sheet.readStatusValues)}</dd>
          </>
        )}
        {facts.full_text_read !== null && (
          <>
            <dt>{t.sheet.fullText}</dt>
            <dd>{facts.full_text_read ? t.sheet.yes : t.sheet.no}</dd>
          </>
        )}
        {facts.limitations.length > 0 && (
          <>
            <dt>{t.sheet.limits}</dt>
            <dd>
              <ul>
                {facts.limitations.map((l) => (
                  <li key={l.en}>{pick(l)}</li>
                ))}
              </ul>
            </dd>
          </>
        )}
      </dl>
      {facts.url !== null && (
        <a className={s.link} href={facts.url} target="_blank" rel="noopener noreferrer">
          {t.sheet.link} <Icon name="arrowUpRight" size={16} />
        </a>
      )}
    </section>
  );
}

function ApiSheet({ value, onClose }: { value: ApiSourceRef; onClose: () => void }) {
  const t = useT();
  return (
    <div className={s.inner} data-testid="source-sheet">
      <div className={s.grab} aria-hidden="true" />
      <header className={s.head}>
        <span className={s.stamp} aria-hidden="true">
          {t.common.source}
        </span>
        <div className={s.headText}>
          <p className={s.label}>{value.label || t.sheet.aboutValue}</p>
          <h2 id="prov-title" className={s.value}>
            {value.value}
          </h2>
        </div>
        <button type="button" className={s.close} onClick={onClose} aria-label={t.common.close}>
          <Icon name="close" />
        </button>
      </header>
      {value.ruleText && (
        <section className={s.arith}>
          <h3>{t.sheet.ruleText}</h3>
          <p>{value.ruleText}</p>
        </section>
      )}
      {value.facts.map((f) => (
        <FactsBlock key={f.id} facts={f} />
      ))}
      {value.note && <p className={s.caveat}>{value.note}</p>}
    </div>
  );
}
