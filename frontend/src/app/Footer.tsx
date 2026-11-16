import { BrandEmblem, BrandWordmark } from './Brand';
import { useSettings, useT } from './settings';
import s from './Footer.module.css';

const REPO_URL = 'https://github.com/solar11781/miaudow';

/** A short footer (member A, 2026-11-15): the brand, the reminder, privacy and code links, the team and licence. */
export function Footer() {
  const t = useT();
  const { lang } = useSettings();
  return (
    <footer className={`${s.footer} surface-forest`}>
      <div className={`container ${s.inner}`}>
        <span className={s.brand}>
          <BrandEmblem width={96} />
          <BrandWordmark height={22} />
        </span>
        <p className={s.support}>{t.common.support}</p>
        <nav className={s.links} aria-label={t.footer.linksLabel}>
          {/* a page of the server, outside the app's hash routes; Vietnamese first, its English part at #en */}
          <a href={lang === 'en' ? '/quyen-rieng-tu#en' : '/quyen-rieng-tu'}>{t.footer.privacy}</a>
          <a href={REPO_URL} target="_blank" rel="noreferrer">
            {t.footer.code}
          </a>
        </nav>
        <p className={s.small}>{t.footer.team}</p>
      </div>
    </footer>
  );
}
