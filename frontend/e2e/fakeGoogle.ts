import type { Page } from '@playwright/test';

// UI-UX-SPEC §12c: the test server runs with sign-in off (playwright.config.ts); these helpers answer
// /api/account/config in the browser and stand in for Google's script, so Google is never called.
// a stand-in for https://accounts.google.com/gsi/client: Google's API with a plain button that signs in with a fake
// token, and Google's stylesheet link, as the real script adds one
const FAKE_GSI = `let done = () => {};
window.google = { accounts: { id: {
  initialize(c) { done = c.callback; }, disableAutoSelect() {}, cancel() {},
  renderButton(el) {
    const css = document.createElement('link'); css.rel = 'stylesheet'; css.href = 'https://accounts.google.com/gsi/style';
    document.head.append(css);
    const b = document.createElement('button'); b.textContent = 'Google'; b.onclick = () => done({ credential: 'fake' });
    el.append(b);
  },
} } };`;

export async function signInOn(page: Page): Promise<string[]> {
  const google: string[] = [];
  await page.route('**/api/account/config', (route) =>
    route.fulfill({ json: { available: true, client_id: 'test.apps.googleusercontent.com' } }),
  );
  await page.route(/^https:\/\/([a-z0-9-]+\.)*google\.com\//, (route) => {
    google.push(route.request().url());
    const css = route.request().url().endsWith('/gsi/style');
    return route.fulfill(
      css ? { contentType: 'text/css', body: '' } : { contentType: 'text/javascript', body: FAKE_GSI },
    );
  });
  return google;
}
