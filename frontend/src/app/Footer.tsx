import { Link } from 'react-router-dom';
import { SavedLink } from '../features/account/SavedLink';
import { useAreas } from './Header';
import { PHOTO_CREDITS } from '../data/media';
import { hazards } from '../data';
import { BrandEmblem, BrandWordmark } from './Brand';
import { Brocade } from '../design-system/Brocade';
import { usePick, useSettings, useT } from './settings';
import s from './Footer.module.css';

export function Footer() {
  const t = useT();
  const pick = usePick();
  const { lang } = useSettings();
  const areas = useAreas().slice(1);
  const built = new Intl.DateTimeFormat(lang === 'vi' ? 'vi-VN' : 'en-GB', {
    dateStyle: 'medium',
    timeStyle: 'short',
    timeZone: 'Asia/Ho_Chi_Minh',
  }).format(new Date(hazards.generated_at));
  return (
    <footer className={`${s.footer} surface-forest grain`}>
      <Brocade />
      <div className={`container ${s.grid}`}>
        <div className={s.brandCol}>
          <span className={s.brand}>
            <BrandEmblem width={150} />
            <BrandWordmark height={26} />
          </span>
          <p className={s.tagline}>{t.footer.tagline}</p>
          <p className={s.support}>{t.common.support}</p>
        </div>
        <nav className={s.links} aria-label={t.nav.main}>
          {areas.map((a) => (
            <Link key={a.to} to={a.to}>
              {a.label}
            </Link>
          ))}
          <SavedLink />
        </nav>
        <div className={s.meta}>
          <p>{t.common.dataLine}</p>
          <p className="mono">
            {t.footer.built}: {built}
          </p>
          <details className={s.credits}>
            <summary>{t.footer.photos}</summary>
            <p>{t.footer.photosLead}</p>
            <ul>
              {PHOTO_CREDITS.map(([slug, m]) => (
                <li key={slug}>
                  <span>{pick(m.caption)}</span>
                  <span>{m.credit ? pick(m.credit) : ''}</span>
                  <span className={s.creditLinks}>
                    {m.license_url && (
                      <a href={m.license_url} target="_blank" rel="noreferrer license">
                        {t.footer.licence}: {m.license}
                      </a>
                    )}
                    {m.source_url && (
                      <a href={m.source_url} target="_blank" rel="noreferrer">
                        {t.footer.source}
                      </a>
                    )}
                  </span>
                </li>
              ))}
            </ul>
          </details>
          <p>{t.footer.team}</p>
        </div>
      </div>
      <hr className="rows-rule" />
    </footer>
  );
}
