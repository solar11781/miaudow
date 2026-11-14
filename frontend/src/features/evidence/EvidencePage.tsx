import { useMemo, useState } from 'react';
import { SOURCES } from '../../domain/sources';
import type { EvidenceKind } from '../../domain/provenance';
import { Icon } from '../../design-system/Icon';
import { Reveal } from '../../design-system/Reveal';
import { SourceValue } from '../provenance/SourceValue';
import { KindBadge } from '../provenance/KindBadge';
import { usePick, useT } from '../../app/settings';
import { CONFLICTS, STATUSES, TOPICS, useClaims, type Claim, type Status, type Topic } from './claims';
import { Datasets } from './Datasets';
import { Quality } from './Quality';
import s from './evidence.module.css';

export function StatusTag({ status }: { status: Status }) {
  const t = useT();
  return (
    <span className={s.status} data-status={status}>
      <i aria-hidden="true" />
      {t.evidence.status[status]}
    </span>
  );
}

function ClaimCard({ claim }: { claim: Claim }) {
  const t = useT();
  const pick = usePick();
  return (
    <article className={s.claim} aria-labelledby={`claim-${claim.id}`}>
      <div className={s.claimTop}>
        <StatusTag status={claim.status} />
        <span className={s.topic}>{t.evidence.topics[claim.topic]}</span>
      </div>
      <h3 id={`claim-${claim.id}`} className={s.conclusion}>
        {pick(claim.conclusion)}
      </h3>
      <p className={s.meaning}>
        <span className={s.step}>{t.evidence.meaning}</span>
        {pick(claim.meaning)}
      </p>
      {claim.refs.length > 0 && (
        <div className={s.values}>
          <span className={s.step}>{t.evidence.value}</span>
          <div className="cluster">
            {claim.refs.map((r) => (
              <SourceValue key={`${r.sourceId}-${r.label}`} size="lg" {...r} />
            ))}
          </div>
        </div>
      )}
      <p className={s.where}>
        <Icon name="book" size={18} />
        <span>
          <span className={s.step}>{t.evidence.source}</span>
          {pick(claim.location)}
        </span>
      </p>
      <details className={s.more}>
        <summary>
          {t.evidence.methodAndLimits}
          <Icon name="chevronDown" size={18} />
        </summary>
        <dl>
          <dt>{t.evidence.method}</dt>
          <dd>{pick(claim.method)}</dd>
          <dt>{t.evidence.appliesTo}</dt>
          <dd>{pick(claim.appliesTo)}</dd>
          <dt>{t.evidence.notProve}</dt>
          <dd>{pick(claim.notProve)}</dd>
        </dl>
      </details>
    </article>
  );
}

const KIND_GROUPS: { kind: EvidenceKind; ids: (keyof typeof SOURCES)[] }[] = [
  { kind: 'study', ids: ['p02', 'p03', 'zhang2011'] },
  { kind: 'standard', ids: ['qd18', 'tcvn8641', 'fao-tm3'] },
  { kind: 'data', ids: ['nasa-power', 'modis', 'nso', 'geoboundaries'] },
  { kind: 'model', ids: ['e012', 'e010'] },
];

export function EvidencePage() {
  const t = useT();
  const pick = usePick();
  const claims = useClaims();
  const [topic, setTopic] = useState<Topic | 'all'>('all');
  const [status, setStatus] = useState<Status | 'all'>('all');
  const shown = useMemo(
    () => claims.filter((c) => (topic === 'all' || c.topic === topic) && (status === 'all' || c.status === status)),
    [claims, topic, status],
  );
  const present = new Set(claims.map((c) => c.status));

  return (
    <main id="main" className={s.page}>
      <section className={`band surface-paper ${s.hero}`} aria-labelledby="ev-title">
        <div className={`container ${s.heroGrid}`}>
          <div className="stack" style={{ ['--gap' as string]: 'var(--s-4)' }}>
            <p className="eyebrow">{t.evidence.eyebrow}</p>
            <h1 id="ev-title" className={`display ${s.title}`}>
              {t.evidence.title}
            </h1>
            <p className="lead">{t.evidence.lead}</p>
          </div>
          <ol className={s.ladder} aria-label={t.evidence.ladderLabel}>
            {t.evidence.ladder.map((step, i) => (
              <li key={step}>
                <span className={s.ladderNum}>{i + 1}</span>
                {step}
              </li>
            ))}
          </ol>
        </div>
      </section>

      <section className="band surface-paper" aria-labelledby="ev-claims" style={{ paddingTop: 0 }}>
        <div className="container stack" style={{ ['--gap' as string]: 'var(--s-6)' }}>
          <div className={s.filters}>
            <h2 id="ev-claims" className="h2">
              {t.evidence.claimsTitle}
            </h2>
            <div className={s.chips} role="radiogroup" aria-label={t.evidence.topicLabel}>
              <button type="button" role="radio" aria-checked={topic === 'all'} onClick={() => setTopic('all')}>
                {t.evidence.all}
              </button>
              {TOPICS.map((x) => (
                <button key={x} type="button" role="radio" aria-checked={topic === x} onClick={() => setTopic(x)}>
                  {t.evidence.topics[x]}
                </button>
              ))}
            </div>
            <div className={s.chips} role="radiogroup" aria-label={t.evidence.statusLabel}>
              <button type="button" role="radio" aria-checked={status === 'all'} onClick={() => setStatus('all')}>
                {t.evidence.allStatuses}
              </button>
              {STATUSES.filter((x) => present.has(x)).map((x) => (
                <button key={x} type="button" role="radio" aria-checked={status === x} onClick={() => setStatus(x)}>
                  {t.evidence.status[x]}
                </button>
              ))}
            </div>
          </div>
          <p className={s.count} role="status">
            {t.evidence.showing(shown.length, claims.length)}
          </p>
          <div className={s.claims}>
            {shown.map((c) => (
              <ClaimCard key={c.id} claim={c} />
            ))}
          </div>
        </div>
      </section>

      <section className="band surface-forest grain" aria-labelledby="ev-conflicts">
        <div className="container stack" style={{ ['--gap' as string]: 'var(--s-6)' }}>
          <Reveal className={s.sectionHead}>
            <p className="eyebrow">{t.evidence.conflictsEyebrow}</p>
            <h2 id="ev-conflicts" className="h1">
              {t.evidence.conflictsTitle}
            </h2>
            <p className="lead">{t.evidence.conflictsLead}</p>
          </Reveal>
          <ol className={s.conflicts}>
            {CONFLICTS.map((c, i) => (
              <li key={c.id}>
                <span className={s.conflictNum} aria-hidden="true">
                  {String(i + 1).padStart(2, '0')}
                </span>
                <div>
                  <h3 className="h3">{pick(c.title)}</h3>
                  <p>{pick(c.body)}</p>
                  <p className={s.conflictSrc}>{pick(c.source)}</p>
                </div>
              </li>
            ))}
          </ol>
        </div>
      </section>

      <Datasets />

      <Quality />

      <section className="band surface-paper" aria-labelledby="ev-sources">
        <div className="container stack" style={{ ['--gap' as string]: 'var(--s-6)' }}>
          <Reveal className={s.sectionHead}>
            <h2 id="ev-sources" className="h1">
              {t.evidence.sourcesTitle}
            </h2>
            <p className="lead">{t.evidence.sourcesLead}</p>
          </Reveal>
          {KIND_GROUPS.map((g) => (
            <div key={g.kind} className={s.group}>
              <h3 className={s.groupTitle}>
                <KindBadge kind={g.kind} />
              </h3>
              <div className={s.sources}>
                {g.ids.map((id) => {
                  const src = SOURCES[id];
                  return (
                    <article key={id} className={s.source}>
                      <h4 className={s.sourceTitle}>{pick(src.title)}</h4>
                      <p className={s.publisher}>{pick(src.publisher)}</p>
                      <dl className={s.facts}>
                        <dt>{t.sheet.where}</dt>
                        <dd>{pick(src.where)}</dd>
                        <dt>{t.sheet.period}</dt>
                        <dd>{pick(src.period)}</dd>
                        <dt>{t.evidence.readStatus}</dt>
                        <dd>{pick(src.howRead)}</dd>
                        <dt>{t.sheet.caveat}</dt>
                        <dd>{pick(src.caveat)}</dd>
                      </dl>
                      {src.url && (
                        <a className={s.link} href={src.url} target="_blank" rel="noreferrer">
                          {t.sheet.link}
                          <Icon name="arrowUpRight" size={18} />
                        </a>
                      )}
                    </article>
                  );
                })}
              </div>
            </div>
          ))}
        </div>
      </section>
    </main>
  );
}
