import { useState } from 'react';
import { YEARS } from '../../data';
import { yearShare } from '../../domain/hazards';
import { CROPS, PLANS, planHasLegume, planProfitMillion } from '../../domain/plans';
import { livingDays } from '../../domain/calendar';
import { SOURCES } from '../../domain/sources';
import { EVIDENCE_ORDER, type EvidenceKind, type SourceId } from '../../domain/provenance';
import { Icon } from '../../design-system/Icon';
import { Media } from '../../design-system/Media';
import { Reveal } from '../../design-system/Reveal';
import { KindBadge } from '../provenance/KindBadge';
import { SourceValue } from '../provenance/SourceValue';
import { useRefs } from '../provenance/useRefs';
import { useProvenance } from '../provenance/ProvenanceProvider';
import { useFormat, usePick, useT } from '../../app/settings';
import s from './officer.module.css';

function Matrix() {
  const t = useT();
  const pick = usePick();
  const f = useFormat();
  const refs = useRefs();
  return (
    <div className={s.matrixWrap} tabIndex={0} role="region" aria-label={t.officer.matrixTitle}>
      <table className={s.matrix}>
        <thead>
          <tr>
            <th scope="col">{t.officer.colPlan}</th><th scope="col">{t.officer.colMoney}</th><th scope="col">{t.officer.colWeather}</th>
            <th scope="col">{t.officer.colWater}</th><th scope="col">{t.officer.colLand}</th>
          </tr>
        </thead>
        <tbody>
          {PLANS.map((p) => {
            const total = planProfitMillion(p);
            return (
              <tr key={p.id}>
                <th scope="row">
                  <span className={s.planId}>{p.current ? t.farmer.current : p.id.toUpperCase()}</span>
                  <span className={s.planSeq}>{p.textOnly ? pick(p.textOnly.sequence) : p.crops.map((c) => pick(CROPS[c.crop].name)).join(' → ')}</span>
                  <span className={s.planSrc}>{SOURCES[p.source].short}</span>
                </th>
                <td>
                  {total !== null ? <SourceValue {...refs.planProfit(p, total)} showSource={SOURCES.p02.short} /> : (
                    p.textOnly && <SourceValue sourceId="p03" kind="study" value={pick(p.textOnly.profitNote)} label={t.officer.colMoney} showSource="P-03" />
                  )}
                  {p.crops.length > 0 && (
                    <details className={s.costs}>
                      <summary>{t.officer.costs} · {t.officer.price}</summary>
                      <ul>
                        {p.crops.map((c) => (
                          <li key={c.key}>
                            <span>{pick(CROPS[c.crop].name)} {c.variety}</span>
                            <span className="mono">{f.n(c.cost)} {t.officer.thousandPerHa} · {f.n(c.price)} {t.officer.perKg}</span>
                          </li>
                        ))}
                      </ul>
                    </details>
                  )}
                </td>
                <td>{p.crops.length ? <><KindBadge kind="derived" compact /><span className={s.cellNote}>{t.officer.weatherCell}</span></> : <span className={s.empty}>—</span>}</td>
                <td>
                  {p.crops.length ? (
                    <ul className={s.waterList}>
                      {[...new Map(p.crops.map((c) => [c.crop, c])).values()].map((c) => {
                        const info = CROPS[c.crop] as { tcvn?: { vi: string; en: string } };
                        return <li key={c.key}><span>{pick(CROPS[c.crop].name)}</span>{info.tcvn ? <SourceValue {...refs.tcvn(c, pick(info.tcvn))} /> : <span className={s.empty}>{t.common.notListed}</span>}</li>;
                      })}
                    </ul>
                  ) : <span className={s.empty}>—</span>}
                </td>
                <td>
                  {p.crops.length ? (
                    <span className={s.land}>
                      <span>{t.farmer.livingDays(livingDays(p))}</span>
                      <span>{planHasLegume(p) ? t.farmer.legumeYes : t.farmer.legumeNo}</span>
                    </span>
                  ) : <span className={s.empty}>—</span>}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

function Registry() {
  const t = useT();
  const pick = usePick();
  const open = useProvenance();
  const [kind, setKind] = useState<EvidenceKind | 'all'>('all');
  const ids = (Object.keys(SOURCES) as SourceId[]).filter((id) => kind === 'all' || SOURCES[id].kind === kind);
  const kinds = EVIDENCE_ORDER.filter((k) => (Object.values(SOURCES)).some((x) => x.kind === k)).concat('illustration');
  return (
    <div className="stack" style={{ ['--gap' as string]: 'var(--s-5)' }}>
      <div className={s.filters} role="radiogroup" aria-label={t.officer.registryTitle}>
        <button type="button" role="radio" aria-checked={kind === 'all'} onClick={() => setKind('all')}>{t.officer.filterAll}</button>
        {kinds.map((k) => (
          <button key={k} type="button" role="radio" aria-checked={kind === k} onClick={() => setKind(k)}>{t.kinds[k]}</button>
        ))}
      </div>
      <ul className={s.registry}>
        {ids.map((id) => {
          const src = SOURCES[id];
          return (
            <li key={id}>
              <button type="button" className={s.regItem} onClick={() => open({ sourceId: id, kind: src.kind, value: src.short, label: pick(src.title) })}>
                <KindBadge kind={src.kind} compact />
                <span className={s.regTitle}>{pick(src.title)}</span>
                <span className={s.regMeta}>{pick(src.publisher)}</span>
                <span className={s.regMeta}>{pick(src.period)} · {pick(src.where)}</span>
                <Icon name="arrowUpRight" size={18} className={s.regArrow} />
              </button>
            </li>
          );
        })}
      </ul>
    </div>
  );
}

export function OfficerPage() {
  const t = useT();
  const f = useFormat();
  const lastDry = [...YEARS].reverse().find((y) => yearShare('drought_rain_any2', y) >= 0.99) ?? (YEARS[0] as number);
  const talk = [t.officer.talk[0], t.officer.talkDrought(lastDry, f.pct(yearShare('drought_rain_any2', lastDry))), t.officer.talk[1]].filter(Boolean) as { do: string; dont: string }[];
  return (
    <main id="main" className="surface-paper">
      <section className={`band ${s.hero}`} aria-labelledby="officer-title">
        <div className={`container ${s.heroGrid}`}>
          <div className="stack" style={{ ['--gap' as string]: 'var(--s-5)' }}>
            <p className="eyebrow">{t.officer.eyebrow}</p>
            <h1 id="officer-title" className="display" style={{ fontSize: 'var(--t-h1)' }}>{t.officer.title}</h1>
            <p className="lead">{t.officer.lead}</p>
            <dl className={s.scope}>
              {t.officer.scope.map((x) => <div key={x.label}><dt>{x.label}</dt><dd>{x.value}</dd></div>)}
            </dl>
          </div>
          <div className={s.heroPhoto}><Media slug="do-luong-lam-son-communal-house" sizes="(min-width: 900px) 420px, 92vw" priority /></div>
        </div>
      </section>

      <section className="band" aria-labelledby="matrix-title" style={{ paddingTop: 0 }}>
        <div className="container stack" style={{ ['--gap' as string]: 'var(--s-5)' }}>
          <Reveal className="stack" style={{ ['--gap' as string]: 'var(--s-3)' }}>
            <h2 id="matrix-title" className="h1">{t.officer.matrixTitle}</h2>
            <p className="lead">{t.officer.matrixLead}</p>
          </Reveal>
          <Reveal><Matrix /></Reveal>
        </div>
      </section>

      <section className={`band surface-forest grain`} aria-labelledby="lineage-title">
        <div className={`container ${s.split}`}>
          <Reveal className="stack" style={{ ['--gap' as string]: 'var(--s-4)' }}>
            <h2 className="h2">{t.officer.twoStudiesTitle}</h2>
            <p className="lead">{t.officer.twoStudiesLead}</p>
          </Reveal>
          <Reveal className="stack" style={{ ['--gap' as string]: 'var(--s-4)' }}>
            <h2 id="lineage-title" className="h2">{t.officer.lineageTitle}</h2>
            <ol className={s.lineage}>
              {t.officer.lineage.map((step, i) => (
                <li key={step.title}>
                  <span className={s.lineNum}>{String(i + 1).padStart(2, '0')}</span>
                  <span className={s.lineBody}><KindBadge kind={step.kind as EvidenceKind} compact /><strong>{step.title}</strong><span>{step.body}</span></span>
                </li>
              ))}
            </ol>
          </Reveal>
        </div>
      </section>

      <section className="band" aria-labelledby="talk-title">
        <div className={`container ${s.split}`}>
          <Reveal className="stack" style={{ ['--gap' as string]: 'var(--s-4)' }}>
            <h2 id="talk-title" className="h2">{t.officer.talkTitle}</h2>
            <ul className={s.talk}>
              {talk.map((x) => (
                <li key={x.do}>
                  <p className={s.do}><Icon name="check" size={16} strokeWidth={2.4} />{x.do}</p>
                  <p className={s.dont}><Icon name="close" size={16} strokeWidth={2.4} />{x.dont}</p>
                </li>
              ))}
            </ul>
          </Reveal>
          <Reveal className="stack" style={{ ['--gap' as string]: 'var(--s-4)' }}>
            <h2 className="h2">{t.officer.gapsTitle}</h2>
            <ul className={s.gaps}>{t.officer.gaps.map((g) => <li key={g}><Icon name="alert" size={18} />{g}</li>)}</ul>
          </Reveal>
        </div>
      </section>

      <section className="band" aria-labelledby="reg-title" style={{ paddingTop: 0 }}>
        <div className="container stack" style={{ ['--gap' as string]: 'var(--s-5)' }}>
          <Reveal className="stack" style={{ ['--gap' as string]: 'var(--s-3)' }}>
            <h2 id="reg-title" className="h1">{t.officer.registryTitle}</h2>
            <p className="lead">{t.officer.registryLead}</p>
          </Reveal>
          <Registry />
        </div>
      </section>
    </main>
  );
}
