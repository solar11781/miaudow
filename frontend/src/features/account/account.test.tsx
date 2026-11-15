// UI-UX-SPEC §12c sign-in screens; Google is a mock and the account calls are spies, so nothing leaves the test.
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { useEffect, type ReactNode } from 'react';
import { act, cleanup, render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { createMemoryRouter, RouterProvider, useLocation } from 'react-router-dom';
import { api, ApiError, type SavedAnswers, type SavedSet } from '../../api';
import { SettingsProvider } from '../../app/settings';
import { vi as text } from '../../i18n/vi';
import { en } from '../../i18n/en';
import { AccountProvider, safeBack, useAccount } from './AccountProvider';
import { SaveAnswers } from './SaveAnswers';
import { SavedPage } from './SavedPage';
import { SignInPage } from './SignInPage';
import { loadGoogle, unloadGoogle, type GoogleId } from './google';

vi.mock('./google', () => ({ loadGoogle: vi.fn(), unloadGoogle: vi.fn() }));

const ON = { available: true, client_id: 'test.apps.googleusercontent.com' } as const;
const OFF = { available: false, client_id: null } as const;
// D-180: a saved set keeps the typed prices (đ/kg) and costs (thousand đ/ha) by crop key
const OWN = { prices: { cc1_spring_peanut: '31357' }, costs: { cc1_spring_peanut: '24689' } };
const NO_OWN = { prices: {}, costs: {} };
const SETS: SavedSet[] = [
  { id: 1, land: 'high_field', years: [2010, 2020], priority: 'income', ...OWN },
  { id: 2, land: 'ask', years: [1998], priority: 'water', ...NO_OWN },
];
const ANSWERS: SavedAnswers = { land: 'canal_end', years: [2010], priority: 'income', ...OWN };
const PLANS = '/nong-dan/phuong-an?ruong=canal_end&nam=2010&uutien=income';
const PLANS_OWN = `${PLANS}&yp.cc1_spring_peanut=31357&yc.cc1_spring_peanut=24689`;
const t = text.account;

function Where() {
  const { pathname, search } = useLocation();
  return <output data-testid="where">{`${pathname}${search}`}</output>;
}

function Seed({ token, children }: { token: string | null; children: ReactNode }) {
  const { signIn } = useAccount();
  useEffect(() => {
    if (token) signIn(token);
  }, [token, signIn]);
  return children;
}

function show(path: string, token: string | null = null) {
  const page = (el: ReactNode) => (
    <Seed token={token}>
      {el}
      <Where />
    </Seed>
  );
  const router = createMemoryRouter(
    [
      { path: '/dang-nhap', element: page(<SignInPage />) },
      { path: '/da-luu', element: page(<SavedPage />) },
      {
        path: '/nong-dan/phuong-an',
        element: page(<SaveAnswers answers={ANSWERS} />),
      },
    ],
    { initialEntries: [path] },
  );
  render(
    <SettingsProvider>
      <AccountProvider>
        <RouterProvider router={router} />
      </AccountProvider>
    </SettingsProvider>,
  );
}

function fakeGoogle() {
  let callback: (answer: { credential: string }) => void = () => undefined;
  const id: GoogleId = {
    initialize: vi.fn((config) => {
      callback = config.callback;
    }),
    renderButton: vi.fn(),
    disableAutoSelect: vi.fn(),
    cancel: vi.fn(),
  };
  vi.mocked(loadGoogle).mockResolvedValue(id);
  return { id, answer: (credential: string) => act(() => callback({ credential })) };
}

const where = () => screen.getByTestId('where').textContent;

beforeEach(() => {
  vi.mocked(loadGoogle).mockReset();
  vi.mocked(unloadGoogle).mockReset();
});
afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});

describe('sign-in page', () => {
  it('says sign-in is not available and never loads Google when the server has it off', async () => {
    vi.spyOn(api.account, 'config').mockResolvedValue(OFF);
    show('/dang-nhap');
    expect(await screen.findByText(t.notAvailable)).toBeTruthy();
    expect(screen.queryByRole('button', { name: t.agree })).toBeNull();
    expect(loadGoogle).not.toHaveBeenCalled();
  });

  it('shows the privacy notice with the full-notice link before Google is loaded', async () => {
    vi.spyOn(api.account, 'config').mockResolvedValue(ON);
    show('/dang-nhap');
    const heading = await screen.findByRole('heading', { name: t.noticeTitle });
    // spec review of PR #53: the plain line names everything the server stores, the Google account id included
    expect(heading.nextElementSibling?.textContent).toBe(
      'Chỉ lưu mã tài khoản Google và câu trả lời của bạn; xóa được bất cứ lúc nào.',
    );
    for (const line of t.notice) expect(screen.getByText(line)).toBeTruthy();
    expect(screen.getByRole('link', { name: t.noticeFull }).getAttribute('href')).toBe('/quyen-rieng-tu');
    expect(loadGoogle).not.toHaveBeenCalled();
  });

  it('starts Google with the client id after the tap, signs in and returns with the answers', async () => {
    vi.spyOn(api.account, 'config').mockResolvedValue(ON);
    const signIn = vi.spyOn(api.account, 'signIn').mockResolvedValue();
    const google = fakeGoogle();
    const back = '/nong-dan/phuong-an?ruong=canal_end&nam=2010&uutien=income';
    show(`/dang-nhap?ve=${encodeURIComponent(back)}`);
    await userEvent.click(await screen.findByRole('button', { name: t.agree }));
    await waitFor(() => expect(google.id.renderButton).toHaveBeenCalled());
    expect(google.id.initialize).toHaveBeenCalledWith(expect.objectContaining({ client_id: ON.client_id }));
    await google.answer('google-id-token');
    await waitFor(() => expect(where()).toBe(back));
    expect(signIn).toHaveBeenCalledWith('google-id-token');
    // H14: Google's script runs only on the sign-in pages, so it is taken off the page on the way back
    expect(unloadGoogle).toHaveBeenCalled();
    // H14: the token stays in memory only
    expect([localStorage.length, sessionStorage.length, document.cookie]).toEqual([0, 0, '']);
  });

  it('goes to the saved answers page when the return address is not one of the app pages', async () => {
    vi.spyOn(api.account, 'config').mockResolvedValue(ON);
    vi.spyOn(api.account, 'signIn').mockResolvedValue();
    vi.spyOn(api.account, 'saved').mockResolvedValue([]);
    const google = fakeGoogle();
    show('/dang-nhap?ve=https%3A%2F%2Fexample.com');
    await userEvent.click(await screen.findByRole('button', { name: t.agree }));
    await waitFor(() => expect(google.id.renderButton).toHaveBeenCalled());
    await google.answer('google-id-token');
    await waitFor(() => expect(where()).toBe('/da-luu'));
  });

  it('says so when Google cannot be loaded, with a retry', async () => {
    vi.spyOn(api.account, 'config').mockResolvedValue(ON);
    vi.mocked(loadGoogle).mockRejectedValue(new Error('offline'));
    show('/dang-nhap');
    await userEvent.click(await screen.findByRole('button', { name: t.agree }));
    expect(await screen.findByText(t.googleFailed)).toBeTruthy();
    expect(screen.getByRole('button', { name: text.common.retry })).toBeTruthy();
  });
});

describe('saved answers page', () => {
  it('says sign-in is not available, with no sign-in link, when the server has it off', async () => {
    vi.spyOn(api.account, 'config').mockResolvedValue(OFF);
    show('/da-luu');
    expect(await screen.findByText(t.notAvailable)).toBeTruthy();
    expect(screen.queryByRole('link', { name: t.signInCta })).toBeNull();
  });

  it('asks to sign in when signed out', async () => {
    vi.spyOn(api.account, 'config').mockResolvedValue(ON);
    show('/da-luu');
    expect(await screen.findByText(t.needSignIn)).toBeTruthy();
    expect(screen.getByRole('link', { name: t.signInCta }).getAttribute('href')).toBe('/dang-nhap?ve=%2Fda-luu');
  });

  it('names each set from its answers and opens it on the plan cards with its typed prices and costs', async () => {
    vi.spyOn(api.account, 'saved').mockResolvedValue(SETS);
    show('/da-luu', 'tok');
    const name = `${text.farmer.lands.high_field.title} · ${t.yearsLabel('2010, 2020')} · ${text.farmer.prios.income.title}`;
    expect(await screen.findByText(name)).toBeTruthy();
    // D-180: the typed numbers come back in the fragment keys yp.<crop key> and yc.<crop key>
    expect(screen.getByRole('link', { name: t.openLabel(name) }).getAttribute('href')).toBe(
      '/nong-dan/phuong-an?ruong=high_field&nam=2010%2C2020&uutien=income&yp.cc1_spring_peanut=31357&yc.cc1_spring_peanut=24689',
    );
    const other = `${text.farmer.lands.ask.title} · ${t.yearsLabel('1998')} · ${text.farmer.prios.water.title}`;
    expect(screen.getByRole('link', { name: t.openLabel(other) }).getAttribute('href')).toBe(
      '/nong-dan/phuong-an?ruong=ask&nam=1998&uutien=water',
    );
  });

  it('deletes one set and loads the list again', async () => {
    const saved = vi.spyOn(api.account, 'saved').mockResolvedValueOnce(SETS).mockResolvedValueOnce(SETS.slice(1));
    const remove = vi.spyOn(api.account, 'remove').mockResolvedValue();
    show('/da-luu', 'tok');
    const name = `${text.farmer.lands.high_field.title} · ${t.yearsLabel('2010, 2020')} · ${text.farmer.prios.income.title}`;
    const open = await screen.findByRole('button', { name: t.removeLabel(name) });
    await userEvent.click(open);
    expect(document.activeElement?.textContent).toBe(t.removeAsk);
    await userEvent.click(screen.getByRole('button', { name: t.removeNo }));
    expect(document.activeElement).toBe(open);
    expect(remove).not.toHaveBeenCalled();
    await userEvent.click(open);
    await userEvent.click(screen.getByRole('button', { name: t.removeYes }));
    expect(remove).toHaveBeenCalledWith('tok', 1);
    expect(await screen.findByText(t.removed)).toBeTruthy();
    await waitFor(() => expect(screen.queryByText(name)).toBeNull());
    expect(saved).toHaveBeenCalledTimes(2);
  });

  it('deletes the account only after the confirm step, then forgets the token', async () => {
    vi.spyOn(api.account, 'config').mockResolvedValue(ON);
    vi.spyOn(api.account, 'saved').mockResolvedValue(SETS);
    const del = vi.spyOn(api.account, 'deleteAccount').mockResolvedValue();
    show('/da-luu', 'tok');
    const open = await screen.findByRole('button', { name: t.deleteAll });
    await userEvent.click(open);
    expect(document.activeElement?.textContent).toBe(t.deleteAllAsk);
    await userEvent.click(screen.getByRole('button', { name: t.deleteAllNo }));
    expect(document.activeElement).toBe(open);
    expect(del).not.toHaveBeenCalled();
    await userEvent.click(open);
    await userEvent.click(screen.getByRole('button', { name: t.deleteAllYes }));
    expect(del).toHaveBeenCalledWith('tok');
    expect(await screen.findByText(t.deletedAll)).toBeTruthy();
    expect(screen.getByRole('link', { name: t.signInCta })).toBeTruthy();
  });

  it('signs out by dropping the token from memory', async () => {
    vi.spyOn(api.account, 'config').mockResolvedValue(ON);
    vi.spyOn(api.account, 'saved').mockResolvedValue(SETS);
    show('/da-luu', 'tok');
    await userEvent.click(await screen.findByRole('button', { name: t.signOut }));
    expect(await screen.findByText(t.signedOut)).toBeTruthy();
    expect(screen.queryByRole('button', { name: t.deleteAll })).toBeNull();
  });

  it('asks to sign in again when the token has expired', async () => {
    vi.spyOn(api.account, 'config').mockResolvedValue(ON);
    vi.spyOn(api.account, 'saved').mockRejectedValue(new ApiError(401, 'not signed in'));
    show('/da-luu', 'tok');
    expect(await screen.findByText(t.expired)).toBeTruthy();
    expect(screen.getByRole('link', { name: t.signInAgain })).toBeTruthy();
  });
});

describe('save these answers', () => {
  it('is hidden while sign-in is not available', async () => {
    const config = vi.spyOn(api.account, 'config').mockResolvedValue(OFF);
    show('/nong-dan/phuong-an?ruong=canal_end&nam=2010&uutien=income');
    await waitFor(() => expect(config).toHaveBeenCalled());
    await act(async () => undefined);
    expect(screen.queryByRole('button', { name: t.save })).toBeNull();
    expect(screen.queryByRole('link', { name: t.saveSignIn })).toBeNull();
  });

  it('leads to the sign-in page and back with the answers when signed out', async () => {
    vi.spyOn(api.account, 'config').mockResolvedValue(ON);
    show('/nong-dan/phuong-an?ruong=canal_end&nam=2010&uutien=income');
    const link = await screen.findByRole('link', { name: t.saveSignIn });
    expect(link.getAttribute('href')).toBe(
      `/dang-nhap?ve=${encodeURIComponent('/nong-dan/phuong-an?ruong=canal_end&nam=2010&uutien=income&luu=1')}`,
    );
  });

  // privacy review of PR #66: Google's script runs on the sign-in page and can read the address, so the way back
  // leaves the yp. and yc. keys out
  it('leaves the typed price and costs out of the way back', async () => {
    vi.spyOn(api.account, 'config').mockResolvedValue(ON);
    show(PLANS_OWN);
    const link = await screen.findByRole('link', { name: t.saveSignIn });
    expect(link.getAttribute('href')).toBe(`/dang-nhap?ve=${encodeURIComponent(`${PLANS}&luu=1`)}`);
  });

  // D-180: the typed numbers wait in memory while the farmer signs in, never in the sign-in page's address or the
  // browser's storage, and come back into the fragment on the plan cards for the pending save
  it('brings the typed price and costs back after signing in, without them in the sign-in address', async () => {
    vi.spyOn(api.account, 'config').mockResolvedValue(ON);
    vi.spyOn(api.account, 'signIn').mockResolvedValue();
    const save = vi.spyOn(api.account, 'save').mockResolvedValue({ id: 3, ...ANSWERS, years: [2010] });
    const google = fakeGoogle();
    show(PLANS_OWN);
    await userEvent.click(await screen.findByRole('link', { name: t.saveSignIn }));
    await waitFor(() => expect(where()).toBe(`/dang-nhap?ve=${encodeURIComponent(`${PLANS}&luu=1`)}`));
    await userEvent.click(await screen.findByRole('button', { name: t.agree }));
    await waitFor(() => expect(google.id.renderButton).toHaveBeenCalled());
    await google.answer('google-id-token');
    expect(await screen.findByText(t.saved)).toBeTruthy();
    expect(save).toHaveBeenCalledWith('google-id-token', ANSWERS);
    await waitFor(() => expect(where()).toBe(PLANS_OWN));
    expect([localStorage.length, sessionStorage.length, document.cookie]).toEqual([0, 0, '']);
  });

  it('does not bring typed numbers to a sign-in that started elsewhere', async () => {
    vi.spyOn(api.account, 'config').mockResolvedValue(ON);
    vi.spyOn(api.account, 'signIn').mockResolvedValue();
    const google = fakeGoogle();
    show(`/dang-nhap?ve=${encodeURIComponent(PLANS)}`);
    await userEvent.click(await screen.findByRole('button', { name: t.agree }));
    await waitFor(() => expect(google.id.renderButton).toHaveBeenCalled());
    await google.answer('google-id-token');
    await waitFor(() => expect(where()).toBe(PLANS));
  });

  it('saves at once on the way back from signing in, then drops the pending mark', async () => {
    vi.spyOn(api.account, 'config').mockResolvedValue(ON);
    const save = vi.spyOn(api.account, 'save').mockResolvedValue({ id: 3, ...ANSWERS, years: [2010] });
    show(`${PLANS_OWN}&luu=1`, 'tok');
    expect(await screen.findByText(t.saved)).toBeTruthy();
    expect(save).toHaveBeenCalledTimes(1);
    expect(save).toHaveBeenCalledWith('tok', ANSWERS);
    await waitFor(() => expect(where()).toBe(PLANS_OWN));
  });

  it('saves land, years, priority and the typed prices and costs with the token', async () => {
    vi.spyOn(api.account, 'config').mockResolvedValue(ON);
    const save = vi.spyOn(api.account, 'save').mockResolvedValue({ id: 3, ...ANSWERS, years: [2010] });
    show(PLANS_OWN, 'tok');
    await userEvent.click(await screen.findByRole('button', { name: t.save }));
    expect(save).toHaveBeenCalledWith('tok', ANSWERS);
    expect(await screen.findByText(t.saved)).toBeTruthy();
    // walkthrough recheck: a second tap cannot store the same set twice
    const done = screen.getByRole('button', { name: t.savedDone });
    expect(done.hasAttribute('disabled')).toBe(true);
    expect(screen.queryByRole('button', { name: t.save })).toBeNull();
  });

  it('is done, not offered again, after the automatic save', async () => {
    vi.spyOn(api.account, 'config').mockResolvedValue(ON);
    vi.spyOn(api.account, 'save').mockResolvedValue({ id: 3, ...ANSWERS, years: [2010] });
    show('/nong-dan/phuong-an?ruong=canal_end&nam=2010&uutien=income&luu=1', 'tok');
    expect((await screen.findByRole('button', { name: t.savedDone })).hasAttribute('disabled')).toBe(true);
  });

  it.each([
    [409, 'saved sets are full', t.full],
    [503, 'sign-in is not available', t.unavailableNow],
  ])('shows the answer to %i', async (status, detail, message) => {
    vi.spyOn(api.account, 'config').mockResolvedValue(ON);
    vi.spyOn(api.account, 'save').mockRejectedValue(new ApiError(status, detail));
    show('/nong-dan/phuong-an?ruong=canal_end&nam=2010&uutien=income', 'tok');
    await userEvent.click(await screen.findByRole('button', { name: t.save }));
    expect(await screen.findByText(message)).toBeTruthy();
  });

  it('asks to sign in again after 401', async () => {
    vi.spyOn(api.account, 'config').mockResolvedValue(ON);
    vi.spyOn(api.account, 'save').mockRejectedValue(new ApiError(401, 'not signed in'));
    show('/nong-dan/phuong-an?ruong=canal_end&nam=2010&uutien=income', 'tok');
    await userEvent.click(await screen.findByRole('button', { name: t.save }));
    expect(await screen.findByText(t.expired)).toBeTruthy();
    expect(screen.getByRole('link', { name: t.signInAgain })).toBeTruthy();
  });
});

// D-180: the typed numbers stay on this phone unless the farmer saves the answers while signed in
describe('privacy texts', () => {
  it('say the typed prices and costs are saved only with a signed-in save, and deleted with the account', () => {
    expect(text.farmer.own.private('Gửi thẻ này')).toBe(
      'Các số bạn nhập chỉ nằm trong địa chỉ trang trên máy này, trừ khi bạn đăng nhập và lưu các câu trả lời: khi đó các số này được lưu cùng, và bị xóa khi bạn xóa tài khoản. Nút "Gửi thẻ này" không kèm các số này.',
    );
    expect(en.farmer.own.private('Share this card')).toBe(
      'The numbers you type stay only in this page\'s address on this phone, unless you sign in and save your answers: then they are saved with them, and deleted when you delete your account. The "Share this card" button leaves them out.',
    );
    expect(t.notice[0]).toContain('giá bán và chi phí bạn tự nhập, nếu có');
    expect(en.account.notice[0]).toContain('the sale prices and costs you typed, if any');
  });
});

describe('return after signing in', () => {
  // D-174: the plan cards and the saved answers page in both path languages; anything else goes to the saved answers
  it.each([
    [
      '/nong-dan/phuong-an?ruong=canal_end&nam=2010&uutien=income',
      '/nong-dan/phuong-an?ruong=canal_end&nam=2010&uutien=income',
    ],
    ['/farmer/plans?ruong=canal_end&nam=2010&uutien=income', '/farmer/plans?ruong=canal_end&nam=2010&uutien=income'],
    ['/da-luu', '/da-luu'],
    ['/saved', '/saved'],
    ['/farmer/plansx', '/da-luu'],
    ['//example.com', '/da-luu'],
    [null, '/da-luu'],
  ])('%s returns to %s', (raw, back) => {
    expect(safeBack(raw)).toBe(back);
  });
});
