import { Link } from 'react-router-dom';
import { hazards } from '../data';
import { BrandMark } from './Brand';
import { useSettings, useT } from './settings';
import s from './Footer.module.css';

export function Footer() {
  const t = useT();
  const { lang } = useSettings();
  const built = new Intl.DateTimeFormat(lang === 'vi' ? 'vi-VN' : 'en-GB', { dateStyle: 'medium', timeStyle: 'short', timeZone: 'Asia/Ho_Chi_Minh' })
    .format(new Date(hazards.generated_at));
  return (
    <footer className={`${s.footer} surface-forest grain`}>
      <div className={`container ${s.grid}`}>
        <div className={s.brandCol}>
          <span className={s.brand}><BrandMark size={44} /><span className={s.name}>Miaudow</span></span>
          <p className={s.tagline}>{t.footer.tagline}</p>
          <p className={s.support}>{t.common.support}</p>
        </div>
        <nav className={s.links} aria-label={t.nav.main}>
          <Link to="/nong-dan" viewTransition>{t.nav.farmer}</Link>
          <Link to="/can-bo" viewTransition>{t.nav.officer}</Link>
          <Link to="/khoa-hoc" viewTransition>{t.nav.science}</Link>
          <Link to="/hoi" viewTransition>{t.nav.assistant}</Link>
        </nav>
        <div className={s.meta}>
          <p>{t.common.dataLine}</p>
          <p className="mono">{t.footer.built}: {built}</p>
          <p>{t.footer.photos}</p>
          <p>{t.footer.team}</p>
        </div>
      </div>
      <hr className="rows-rule" />
    </footer>
  );
}
