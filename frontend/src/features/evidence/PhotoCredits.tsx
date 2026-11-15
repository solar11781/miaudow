import { PHOTO_CREDITS } from '../../data/media';
import { usePick, useT } from '../../app/settings';
import s from './PhotoCredits.module.css';

/** Author, licence and source page of every photograph (the CC BY and CC BY-SA licences ask for them; UI-UX-SPEC 12b). */
export function PhotoCredits() {
  const t = useT();
  const pick = usePick();
  return (
    <section className="band surface-paper" aria-labelledby="ev-photos">
      <div className={`container ${s.credits}`}>
        <h2 id="ev-photos" className="h2">
          {t.evidence.photosTitle}
        </h2>
        <p>{t.evidence.photosLead}</p>
        <ul>
          {PHOTO_CREDITS.map(([slug, m]) => (
            <li key={slug}>
              <span>{pick(m.caption)}</span>
              <span>{m.credit ? pick(m.credit) : ''}</span>
              <span className={s.creditLinks}>
                {m.license_url && (
                  <a href={m.license_url} target="_blank" rel="noreferrer license">
                    {t.evidence.photoLicence}: {m.license}
                  </a>
                )}
                {m.source_url && (
                  <a href={m.source_url} target="_blank" rel="noreferrer">
                    {t.evidence.photoSource}
                  </a>
                )}
              </span>
            </li>
          ))}
        </ul>
      </div>
    </section>
  );
}
