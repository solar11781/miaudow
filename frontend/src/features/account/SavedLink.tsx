import type { ReactNode } from 'react';
import { Link } from 'react-router-dom';
import { useT } from '../../app/settings';
import { useSignInAvailable } from './AccountProvider';

/** The way to the saved answers from any phone, shown only while sign-in is on (walkthrough of PR #53). */
export function SavedLink({ className, children }: { className?: string; children?: ReactNode }) {
  const t = useT();
  if (!useSignInAvailable()) return null;
  return (
    <Link to="/da-luu" className={className} viewTransition>
      {t.account.savedTitle}
      {children}
    </Link>
  );
}
