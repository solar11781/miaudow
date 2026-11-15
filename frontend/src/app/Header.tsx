import { useEffect, useRef, useState } from 'react';
import { Link, NavLink, useLocation, useNavigate } from 'react-router-dom';
import { pathFor, useLocalTo } from './paths';
import { ButtonLink } from '../design-system/Button';
import { Icon, type IconName } from '../design-system/Icon';
import { BrandMark, BrandWordmark } from './Brand';
import { SavedLink } from '../features/account/SavedLink';
import { useSettings, useT, type Theme } from './settings';
import s from './Header.module.css';

const NEXT_THEME: Record<Theme, Theme> = { auto: 'light', light: 'dark', dark: 'auto' };
const THEME_ICON: Record<Theme, IconName> = { auto: 'reset', light: 'sun', dark: 'moon' };

function Settings({ inMenu, farmer }: { inMenu?: boolean; farmer?: boolean }) {
  const t = useT();
  const { lang, setLang, lite, setLite, theme, setTheme } = useSettings();
  const { pathname, search } = useLocation();
  const navigate = useNavigate();
  // D-174: the other language's path of the same page, with the answers kept
  const switchLang = () => {
    const other = lang === 'vi' ? 'en' : 'vi';
    navigate({ pathname: pathFor(pathname, other), search }, { replace: true, preventScrollReset: true });
    setLang(other);
  };
  const themeLabel = { auto: t.nav.themeAuto, light: t.nav.themeLight, dark: t.nav.themeDark }[theme];
  return (
    <div className={inMenu ? s.settingsMenu : farmer ? s.settingsFarmer : s.settings}>
      <button
        type="button"
        role="switch"
        aria-checked={lite}
        className={s.switch}
        onClick={() => setLite(!lite)}
        title={t.nav.liteHelp}
      >
        <span className={s.track} aria-hidden="true">
          <span className={s.thumb} />
        </span>
        <span>{t.nav.lite}</span>
      </button>
      <button
        type="button"
        className={s.chip}
        onClick={() => setTheme(NEXT_THEME[theme])}
        aria-label={`${t.nav.theme}: ${themeLabel}`}
        title={`${t.nav.theme}: ${themeLabel}`}
      >
        <Icon name={THEME_ICON[theme]} size={17} /> {inMenu && <span>{themeLabel}</span>}
      </button>
      <button
        type="button"
        className={s.chip}
        onClick={switchLang}
        aria-label={`${t.meta.other} · ${t.meta.otherLabel}`}
        lang={lang === 'vi' ? 'en' : 'vi'}
      >
        <Icon name="globe" size={17} /> <span>{t.meta.other}</span>
      </button>
    </div>
  );
}

/** The areas, in the order a visitor meets them. */
export function useAreas() {
  const t = useT();
  const { lang } = useSettings();
  return [
    { to: '/', label: t.nav.home, end: true },
    { to: '/nong-dan', label: t.nav.farmer },
    { to: '/can-bo', label: t.nav.officer },
    { to: '/khoa-hoc', label: t.nav.science },
    { to: '/phuong-phap', label: t.nav.method },
    { to: '/bang-chung', label: t.nav.evidence },
    { to: '/tro-ly', label: t.nav.assistant },
  ].map((a) => ({ ...a, to: pathFor(a.to, lang) }));
}

/** Farmer routes get a flat header: the brand (home) and the settings, no menu and no other links (UI-UX-SPEC H12). */
function FarmerHeader() {
  const t = useT();
  const local = useLocalTo();
  return (
    <header className={`${s.header} ${s.paper}`}>
      <div className={`container ${s.bar}`}>
        <Link to={local('/')} className={s.brand}>
          <BrandMark />
          <span className={s.word}>
            <BrandWordmark height={18} className={s.wordmark} />
            <span className={s.tag}>{t.nav.farmer}</span>
          </span>
        </Link>
        <Settings farmer />
      </div>
    </header>
  );
}

export function Header({ tone }: { tone: 'forest' | 'paper' | 'overlay' }) {
  const { pathname } = useLocation();
  if (pathFor(pathname, 'vi').startsWith('/nong-dan')) return <FarmerHeader />;
  return <SiteHeader tone={tone} />;
}

function SiteHeader({ tone }: { tone: 'forest' | 'paper' | 'overlay' }) {
  const t = useT();
  const local = useLocalTo();
  const { pathname } = useLocation();
  const menu = useRef<HTMLDialogElement>(null);
  const [scrolled, setScrolled] = useState(false);

  useEffect(() => {
    const on = () => setScrolled(window.scrollY > 8);
    on();
    window.addEventListener('scroll', on, { passive: true });
    return () => window.removeEventListener('scroll', on);
  }, []);
  useEffect(() => {
    menu.current?.close();
  }, [pathname]);

  const links = useAreas();

  return (
    <header
      className={[
        s.header,
        tone === 'paper' ? s.paper : 'surface-forest',
        tone === 'overlay' ? s.overlay : '',
        scrolled ? s.scrolled : '',
      ].join(' ')}
    >
      <div className={`container ${s.bar}`}>
        <Link to={local('/')} className={s.brand}>
          <BrandMark />
          <span className={s.word}>
            <BrandWordmark height={18} className={s.wordmark} />
            <span className={s.tag}>{t.nav.tagline}</span>
          </span>
        </Link>
        <nav className={s.nav} aria-label={t.nav.main}>
          {links.map((l) => (
            <NavLink
              key={l.to}
              to={l.to}
              end={l.end}
              className={({ isActive }) => [s.link, isActive ? s.active : ''].join(' ')}
            >
              {l.label}
            </NavLink>
          ))}
        </nav>
        <Settings />
        <ButtonLink to="/nong-dan/ruong" icon="arrowUpRight" className={s.cta}>
          {t.nav.start}
        </ButtonLink>
        <button type="button" className={s.menuBtn} onClick={() => menu.current?.showModal()} aria-label={t.nav.menu}>
          <Icon name="menu" size={22} />
        </button>
      </div>

      <dialog
        ref={menu}
        className={`${s.menu} surface-forest`}
        aria-label={t.nav.main}
        onClick={(e) => {
          if (e.target === e.currentTarget) menu.current?.close();
        }}
      >
        <div className={s.menuInner}>
          <div className={s.menuHead}>
            <span className={s.brand}>
              <BrandMark />
              <BrandWordmark height={18} className={s.wordmark} />
            </span>
            <button
              type="button"
              className={s.menuClose}
              onClick={() => menu.current?.close()}
              aria-label={t.nav.closeMenu}
            >
              <Icon name="close" size={22} />
            </button>
          </div>
          <nav className={s.menuNav} aria-label={t.nav.main}>
            {links.map((l) => (
              <NavLink
                key={l.to}
                to={l.to}
                end={l.end}
                className={({ isActive }) => [s.menuLink, isActive ? s.active : ''].join(' ')}
              >
                {l.label}
                <Icon name="arrowRight" size={20} />
              </NavLink>
            ))}
            <SavedLink className={s.menuLink}>
              <Icon name="arrowRight" size={20} />
            </SavedLink>
          </nav>
          <Settings inMenu />
        </div>
      </dialog>
    </header>
  );
}
