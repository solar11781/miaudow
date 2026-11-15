import qualityJson from '@data/quality.json';
import type { Bilingual } from '../../domain/provenance';
import { Icon } from '../../design-system/Icon';
import { Reveal } from '../../design-system/Reveal';
import { usePick, useSettings, useT } from '../../app/settings';
import s from './evidence.module.css';

type QStatus = 'pass' | 'warn' | 'fail';
interface Check {
  check_id: string;
  category: string;
  dataset_id: string | null;
  status: QStatus;
  detail: Bilingual;
}
interface Report {
  generated_at: string;
  script: string;
  counts: Record<QStatus | 'total', number>;
  checks: Check[];
}

const REPORT = qualityJson as unknown as Report;
const STATUSES: QStatus[] = ['pass', 'warn', 'fail'];

/** The data-quality report of pipeline/check_quality.py, shown as written: counts, every warning, every failure. */
export function Quality() {
  const t = useT();
  const { lang } = useSettings();
  const when = new Intl.DateTimeFormat(lang === 'vi' ? 'vi-VN' : 'en-GB', {
    dateStyle: 'medium',
    timeStyle: 'short',
    timeZone: 'Asia/Ho_Chi_Minh',
  }).format(new Date(REPORT.generated_at));
  const cats = [...new Set(REPORT.checks.map((c) => c.category))];
  const catLabel = (c: string) => t.quality.categories[c as keyof typeof t.quality.categories] ?? c;
  const of = (st: QStatus) => REPORT.checks.filter((c) => c.status === st);
  return (
    <section className="band surface-paper" aria-labelledby="ev-quality" style={{ paddingTop: 0 }}>
      <div className="container stack" style={{ ['--gap' as string]: 'var(--s-6)' }}>
        <Reveal className={s.sectionHead}>
          <h2 id="ev-quality" className="h1">
            {t.quality.title}
          </h2>
          <p className="lead">{t.quality.lead(REPORT.counts.total)}</p>
        </Reveal>
        <div className={s.qTiles}>
          {STATUSES.map((st) => (
            <p key={st} className={s.qTile} data-status={st}>
              <strong className="num">{REPORT.counts[st]}</strong>
              {t.quality.status[st]}
            </p>
          ))}
        </div>
        <p className={s.qCats}>
          <span>{t.quality.byCategory}:</span>
          {cats.map((c) => (
            <span key={c}>
              {catLabel(c)} <span className="num">{REPORT.checks.filter((x) => x.category === c).length}</span>
            </span>
          ))}
        </p>
        {of('fail').length > 0 && <CheckList title={t.quality.failTitle} checks={of('fail')} catLabel={catLabel} />}
        <CheckList title={t.quality.warnTitle} checks={of('warn')} catLabel={catLabel} />
        <details className={s.qAll}>
          <summary>
            {t.quality.allTitle(of('pass').length)}
            <Icon name="chevronDown" size={18} />
          </summary>
          <CheckList checks={of('pass')} catLabel={catLabel} />
        </details>
        <p className="muted mono">{t.quality.script(REPORT.script, when)}</p>
      </div>
    </section>
  );
}

function CheckList({ title, checks, catLabel }: { title?: string; checks: Check[]; catLabel: (c: string) => string }) {
  const pick = usePick();
  return (
    <div className="stack" style={{ ['--gap' as string]: 'var(--s-3)' }}>
      {title && <h3 className="h3">{title}</h3>}
      <ul className={s.qList}>
        {checks.map((c) => (
          <li key={c.check_id} className={s.qItem} data-status={c.status}>
            <span className={s.qCat}>
              {catLabel(c.category)}
              {c.dataset_id ? ` · ${c.dataset_id}` : ''}
            </span>
            <span>{pick(c.detail)}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}
