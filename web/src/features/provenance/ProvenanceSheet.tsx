import { forwardRef } from 'react';
import { SOURCES } from '../../domain/sources';
import type { SourceRef } from '../../domain/provenance';
import { Icon } from '../../design-system/Icon';
import { KindBadge } from './KindBadge';
import { usePick, useT } from '../../app/settings';
import s from './ProvenanceSheet.module.css';

interface Props {
  value: SourceRef | null;
  onClose: () => void;
}

export const ProvenanceSheet = forwardRef<HTMLDialogElement, Props>(function ProvenanceSheet({ value, onClose }, ref) {
  const t = useT();
  const pick = usePick();
  const src = value ? SOURCES[value.sourceId] : null;
  return (
    <dialog
      ref={ref}
      className={s.sheet}
      aria-labelledby="prov-title"
      onClose={onClose}
      onClick={(e) => { if (e.target === e.currentTarget) onClose(); }}
    >
      {value && src && (
        <div className={s.inner}>
          <div className={s.grab} aria-hidden="true" />
          <header className={s.head}>
            <span className={s.stamp} aria-hidden="true">{t.common.source}</span>
            <div className={s.headText}>
              <p className={s.label}>{value.label || t.sheet.aboutValue}</p>
              <h2 id="prov-title" className={s.value}>{value.value}</h2>
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
                  <li key={id}><KindBadge kind={SOURCES[id].kind} compact /> <span>{SOURCES[id].short}</span></li>
                ))}
              </ol>
            </section>
          )}

          <dl className={s.facts}>
            <dt>{t.sheet.from}</dt><dd>{pick(src.title)}</dd>
            <dt>{t.sheet.publisher}</dt><dd>{pick(src.publisher)}</dd>
            <dt>{t.sheet.where}</dt><dd>{pick(src.where)}</dd>
            <dt>{t.sheet.period}</dt><dd>{pick(src.period)}</dd>
            <dt>{t.sheet.method}</dt><dd>{pick(src.method)}</dd>
            <dt>{t.sheet.howRead}</dt><dd>{pick(src.howRead)}</dd>
            {src.licence && (<><dt>{t.sheet.licence}</dt><dd>{pick(src.licence)}</dd></>)}
          </dl>

          <p className={s.caveat}><strong>{t.sheet.caveat}:</strong> {pick(src.caveat)}</p>

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
