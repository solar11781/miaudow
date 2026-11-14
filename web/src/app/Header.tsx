import { useEffect, useRef, useState } from 'react';
import { Link, NavLink, useLocation } from 'react-router-dom';
import { ButtonLink } from '../design-system/Button';
import { Icon, type IconName } from '../design-system/Icon';
import { BrandMark } from './Brand';
import { useSettings, useT, type Theme } from './settings';
import s from './Header.module.css';

const NEXT_THEME: Record<Theme, Theme> = { auto: 'light', light: 'dark', dark: 'auto' };
const THEME_ICON: Record<Theme, IconName> = { auto: 'reset', light: 'sun', dark: 'moon' };

function Settings({ inMenu, farmer }: { inMenu?: boolean; farmer?: boolean }) {
  const t = useT();
  const { lang, setLang, lite, setLite, theme, setTheme } = useSettings();
  const themeLabel = { auto: t.nav.themeAuto, light: t.nav.themeLight, dark: t.nav.themeDark }[theme];
  return (
    <div className={inMenu ? s.settingsMenu : farmer ? s.settingsFarmer : s.settings}>
      <button type="button" className={s.chip} aria-pressed={lite} onClick={() => setLite(!lite)} title={t.nav.liteHelp}>
        <Icon name="feather" size={17} /> <span>{t.nav.lite}</span>
      </button>
      <button type="button" className={s.chip} onClick={() => setTheme(NEXT_THEME[theme])} aria-label={`${t.nav.theme}: ${themeLabel}`} title={`${t.nav.theme}: ${themeLabel}`}>
        <Icon name={THEME_ICON[theme]} size={17} /> {inMenu && <span>{themeLabel}</span>}
      </button>
      <button type="button" className={s.chip} onClick={() => setLang(lang === 'vi' ? 'en' : 'vi')} aria-label={`${t.meta.other} · ${t.meta.otherLabel}`} lang={lang === 'vi' ? 'en' : 'vi'}>
        <Icon name="globe" size={17} /> <span>{t.meta.other}</span>
      </button>
    </div>
  );
}

/** The six areas, in the order a visitor meets them. */
export function useAreas() {
  const t = useT();
  return [
    { to: '/', label: t.nav.home, end: true },
    { to: '/nong-dan', label: t.nav.farmer },
    { to: '/can-bo', label: t.nav.officer },
    { to: '/khoa-hoc', label: t.nav.science },
    { to: '/bang-chung', label: t.nav.evidence },
    { to: '/tro-ly', label: t.nav.assistant },
  ];
}

/** Farmer routes get a flat header: the brand (home) and the settings, no menu and no other links (UI-UX-SPEC H12). */
function FarmerHeader() {
  const t = useT();
  return (
    <header className={`${s.header} ${s.paper}`}>
      <div className={`container ${s.bar}`}>
        <Link to="/" className={s.brand} viewTransition aria-label={`Miaudow · ${t.nav.home}`}>
          <BrandMark />
          <span className={s.word}><span className={s.name}>Miaudow</span><span className={s.tag}>{t.nav.farmer}</span></span>
        </Link>
        <Settings farmer />
      </div>
    </header>
  );
}

export function Header({ tone }: { tone: 'forest' | 'paper' }) {
  const { pathname } = useLocation();
  if (pathname.startsWith('/nong-dan')) return <FarmerHeader />;
  return <SiteHeader tone={tone} />;
}

function SiteHeader({ tone }: { tone: 'forest' | 'paper' }) {
  const t = useT();
  const { pathname } = useLocation();
  const menu = useRef<HTMLDialogElement>(null);
  const [scrolled, setScrolled] = useState(false);

  useEffect(() => {
    const on = () => setScrolled(window.scrollY > 8);
    on();
    window.addEventListener('scroll', on, { passive: true });
    return () => window.removeEventListener('scroll', on);
  }, []);
  useEffect(() => { menu.current?.close(); }, [pathname]);

  const links = useAreas();

  return (
    <header className={[s.header, tone === 'forest' ? 'surface-forest' : s.paper, scrolled ? s.scrolled : ''].join(' ')}>
      <div className={`container ${s.bar}`}>
        <Link to="/" className={s.brand} viewTransition>
          <BrandMark />
          <span className={s.word}>
            <span className={s.name}>Miaudow</span>
            <span className={s.tag}>Đồng lúa Nghệ An</span>
          </span>
        </Link>
        <nav className={s.nav} aria-label={t.nav.main}>
          {links.map((l) => (
            <NavLink key={l.to} to={l.to} end={l.end} viewTransition className={({ isActive }) => [s.link, isActive ? s.active : ''].join(' ')}>
              {l.label}
            </NavLink>
          ))}
        </nav>
        <Settings />
        <ButtonLink to="/nong-dan/ruong" icon="arrowUpRight" className={s.cta}>{t.nav.start}</ButtonLink>
        <button type="button" className={s.menuBtn} onClick={() => menu.current?.showModal()} aria-label={t.nav.menu}>
          <Icon name="menu" size={22} />
        </button>
      </div>

      <dialog ref={menu} className={`${s.menu} surface-forest`} aria-label={t.nav.main} onClick={(e) => { if (e.target === e.currentTarget) menu.current?.close(); }}>
        <div className={s.menuInner}>
          <div className={s.menuHead}>
            <span className={s.brand}><BrandMark /><span className={s.name}>Miaudow</span></span>
            <button type="button" className={s.menuClose} onClick={() => menu.current?.close()} aria-label={t.nav.closeMenu}>
              <Icon name="close" size={22} />
            </button>
          </div>
          <nav className={s.menuNav} aria-label={t.nav.main}>
            {links.map((l) => (
              <NavLink key={l.to} to={l.to} end={l.end} viewTransition className={({ isActive }) => [s.menuLink, isActive ? s.active : ''].join(' ')}>
                {l.label}
                <Icon name="arrowRight" size={20} />
              </NavLink>
            ))}
          </nav>
          <Settings inMenu />
        </div>
      </dialog>
    </header>
  );
}
