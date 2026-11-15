// Every page loads its code on demand, so on a slow phone the old page stays on screen while the next one loads; the
// menu must follow what the person taps, not when that code arrives (flaky T32, audit item 70).
import { afterEach, describe, expect, it, vi } from 'vitest';
import { act, cleanup, render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { createMemoryRouter, Outlet, RouterProvider } from 'react-router-dom';
import { api } from '../api';
import { AccountProvider } from '../features/account/AccountProvider';
import { vi as text } from '../i18n/vi';
import { Header } from './Header';
import { SettingsProvider } from './settings';

async function show() {
  let arrive: () => void = () => undefined;
  const code = new Promise<void>((resolve) => (arrive = resolve));
  const router = createMemoryRouter([
    {
      element: (
        <>
          <Header tone="paper" />
          <Outlet />
        </>
      ),
      children: [
        { path: '/', element: <h1>start</h1> },
        {
          path: '/can-bo',
          lazy: async () => {
            await code;
            return { Component: () => <h1>officer</h1> };
          },
        },
      ],
    },
  ]);
  render(
    <SettingsProvider>
      <AccountProvider>
        <RouterProvider router={router} />
      </AccountProvider>
    </SettingsProvider>,
  );
  await screen.findByText('start');
  const menu = document.querySelector('dialog') as HTMLDialogElement;
  return { router, menu, arrive: (going?: Promise<void>) => act(async () => (arrive(), await going)) };
}

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});

describe('site menu on a slow connection', () => {
  it('stays open when it was opened while the next page was still loading', async () => {
    vi.spyOn(api.account, 'config').mockResolvedValue({ available: false, client_id: null });
    const { router, menu, arrive } = await show();
    const going = router.navigate('/can-bo');
    await userEvent.click(screen.getByRole('button', { name: text.nav.menu }));
    expect(menu.open).toBe(true);
    await arrive(going);
    expect(await screen.findByText('officer')).toBeTruthy();
    expect(menu.open).toBe(true);
  });

  it('closes as soon as a link in it is tapped, before the next page has loaded', async () => {
    vi.spyOn(api.account, 'config').mockResolvedValue({ available: false, client_id: null });
    const { menu, arrive } = await show();
    await userEvent.click(screen.getByRole('button', { name: text.nav.menu }));
    await userEvent.click(menu.querySelector('a[href="/can-bo"]') as HTMLAnchorElement);
    expect(menu.open).toBe(false);
    await arrive();
  });
});
