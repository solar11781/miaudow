import { Outlet, ScrollRestoration, useLocation } from 'react-router-dom';
import { Fragment, Suspense, useEffect, useState } from 'react';
import { Header } from './Header';
import { Footer } from './Footer';
import { pathFor } from './paths';
import { useSettings, useT } from './settings';
import { api, SNAPSHOT_MODE } from '../api';
import { useApi } from '../hooks/useApi';
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

/** Demo-day offline copy (04-TECH-DESIGN section 9): on every page, so its answers are never taken for the live server's. */
function SnapshotNotice() {
  const t = useT();
  const { lang } = useSettings();
  const [index] = useApi(api.snapshot, 'snapshot');
  const madeAt =
    index.status === 'ok'
      ? new Intl.DateTimeFormat(lang === 'vi' ? 'vi-VN' : 'en-GB', {
          dateStyle: 'short',
          timeStyle: 'short',
          timeZone: 'Asia/Ho_Chi_Minh',
        }).format(new Date(index.data.made_at))
      : null;
  return (
    <p className={s.offline} role="status" data-testid="snapshot-notice">
      {t.snapshot.notice(madeAt)}
    </p>
  );
}

/** The home hero runs under a see-through header; other dark-topped areas get a dark header. */
const tone = (path: string) => (path === '/' ? 'overlay' : path.startsWith('/khoa-hoc') ? 'forest' : 'paper');

export function Layout() {
  const t = useT();
  const { pathname } = useLocation();
  const { lang } = useSettings();
  return (
    <>
      <a className="skip" href="#main">
        {t.nav.skip}
      </a>
      <Header tone={tone(pathFor(pathname, 'vi'))} />
      {SNAPSHOT_MODE ? <SnapshotNotice /> : <OfflineNotice />}
      <Suspense
        fallback={
          <div className={s.loading} role="status">
            {t.common.loading}
          </div>
        }
      >
        <Fragment key={lang}>
          <Outlet />
        </Fragment>
      </Suspense>
      <Footer />
      <ScrollRestoration />
    </>
  );
}
