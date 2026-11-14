import { Outlet, ScrollRestoration, useLocation } from 'react-router-dom';
import { Suspense, useEffect, useState } from 'react';
import { Header } from './Header';
import { Footer } from './Footer';
import { useT } from './settings';
import s from './Layout.module.css';

function OfflineNotice() {
  const t = useT();
  const [offline, setOffline] = useState(() => typeof navigator !== 'undefined' && navigator.onLine === false);
  useEffect(() => {
    const on = () => setOffline(false);
    const off = () => setOffline(true);
    window.addEventListener('online', on);
    window.addEventListener('offline', off);
    return () => {
      window.removeEventListener('online', on);
      window.removeEventListener('offline', off);
    };
  }, []);
  if (!offline) return null;
  return (
    <p className={s.offline} role="status">
      {t.errors.offline}
    </p>
  );
}

/** The home hero runs under a see-through header; other dark-topped areas get a dark header. */
const tone = (path: string) => (path === '/' ? 'overlay' : path.startsWith('/khoa-hoc') ? 'forest' : 'paper');

export function Layout() {
  const t = useT();
  const { pathname } = useLocation();
  return (
    <>
      <a className="skip" href="#main">
        {t.nav.skip}
      </a>
      <Header tone={tone(pathname)} />
      <OfflineNotice />
      <Suspense
        fallback={
          <div className={s.loading} role="status">
            {t.common.loading}
          </div>
        }
      >
        <Outlet />
      </Suspense>
      <Footer />
      <ScrollRestoration />
    </>
  );
}
