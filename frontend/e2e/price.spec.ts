import AxeBuilder from '@axe-core/playwright';
import { expect, test, type Page } from '@playwright/test';

// UI-UX-SPEC section 12d, D-163, H14: the farmer's own price and costs are worked out in the browser; they stay in
// the URL fragment, no request carries them and nothing is stored
const PLANS_URL = '/#/nong-dan/phuong-an?ruong=canal_end&nam=2010,2020&uutien=income';
const PRICE = '31357'; // digits that appear nowhere else, so a request that carries them is found
const COST = '24689';

async function typeNumbers(page: Page) {
  const card = page.locator('#the-cc1');
  await card.getByRole('button', { name: 'Tính với giá bán và chi phí của bạn' }).click();
  await card.getByRole('spinbutton', { name: /^Lạc.*Giá bán của bạn/ }).fill(PRICE);
  await card.getByRole('spinbutton', { name: /^Lạc.*Chi phí của bạn/ }).fill(COST);
  return card;
}

test('T4 T14 your price and costs: worked out in the browser, never in a request, nothing stored', async ({ page }) => {
  const sent: string[] = [];
  page.on('request', (r) => {
    // an antivirus on a team laptop injects its own script into every page; that request is not the app's
    if (new URL(r.url()).hostname.endsWith('.kaspersky-labs.com')) return;
    sent.push([r.method(), r.url(), r.postData() ?? '', JSON.stringify(r.headers())].join(' '));
  });
  const storage = () =>
    page.evaluate(() => ({
      counts: [localStorage.length, sessionStorage.length, document.cookie.length],
      text: JSON.stringify([{ ...localStorage }, { ...sessionStorage }, document.cookie]),
    }));
  await page.goto(PLANS_URL);
  const card = await typeNumbers(page);
  // 3.91 t/ha (P-02 Table 12, peanut) x 31,357 đ/kg = 122,605.87 thousand đ/ha; minus 24,689 = 97,916.87
  const own = card.getByTestId('card-cc1-own');
  await expect(own).toContainText('Tổng thu theo giá của bạn, chưa trừ chi phí: 122.606 nghìn đồng/ha');
  await expect(own).toContainText('Còn lại sau chi phí bạn nhập: 97.917 nghìn đồng/ha');
  await expect(own).toContainText('không phải sản lượng ruộng nhà bạn');

  // T4: numeric fields only, no text field
  expect(await page.locator('input[type=text], input[type=search], input[type=email], input[type=tel]').count()).toBe(
    0,
  );
  expect(await page.locator('input:not([type]), textarea').count()).toBe(0);
  expect(await card.locator('input[type=number]').count()).toBe(6); // a price and a cost for each of the 3 crops

  // H14: nothing in localStorage, sessionStorage or cookies
  expect((await storage()).counts).toEqual([0, 0, 0]);

  // section 12d: the numbers stay in the fragment and survive a reload
  await expect(page).toHaveURL(new RegExp(`#.*yp[.]cc1_spring_peanut=${PRICE}`));
  await page.reload();
  await expect(page.locator('#the-cc1').getByTestId('card-cc1-own')).toContainText('122.606 nghìn đồng/ha');
  // on a reload the router's scroll restoration keeps scroll positions under random keys; never the typed numbers
  const after = (await storage()).text;
  expect(after).not.toContain(PRICE);
  expect(after).not.toContain(COST);

  // H14: no request (URL, body or headers such as Referer) carried them
  expect(sent.length).toBeGreaterThan(0);
  for (const r of sent) {
    expect(r, r.slice(0, 200)).not.toContain(PRICE);
    expect(r, r.slice(0, 200)).not.toContain(COST);
  }
});

test('T31 a shared card leaves your price and costs out', async ({ page, context, browserName }, info) => {
  test.skip(info.project.name !== 'desktop-1440' || browserName !== 'chromium', 'clipboard check on desktop only');
  await context.grantPermissions(['clipboard-read', 'clipboard-write']);
  await page.goto(PLANS_URL);
  const card = await typeNumbers(page);
  await card.getByRole('button', { name: 'Gửi thẻ này' }).click();
  await expect(card).toContainText('Đã chép liên kết của thẻ này');
  const copied = await page.evaluate(() => navigator.clipboard.readText());
  expect(copied).toContain('the=cc1');
  expect(copied).not.toContain(PRICE);
  expect(copied).not.toContain(COST);
});

test('T6 T7 T8 the open form: 44 px targets, 17 px text and no WCAG 2.2 AA violation, with a wrong entry', async ({
  page,
}) => {
  await page.emulateMedia({ reducedMotion: 'reduce' });
  await page.goto(PLANS_URL);
  const card = await typeNumbers(page);
  await card.getByRole('spinbutton', { name: /^Đậu xanh.*Giá bán của bạn/ }).fill('-3');
  await expect(card.getByText('Hãy nhập số nguyên, từ 0 trở lên. Số này chưa được dùng.')).toBeVisible();
  const form = card.locator('[id="card-cc1-own-form"]');
  for (const target of await form.locator('input, button').all()) {
    const box = await target.boundingBox();
    expect(box?.height ?? 0).toBeGreaterThanOrEqual(44);
    expect(box?.width ?? 0).toBeGreaterThanOrEqual(44);
  }
  const small = await form.evaluate((root) => {
    const out: string[] = [];
    const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
    for (let n = walker.nextNode(); n; n = walker.nextNode()) {
      const el = n.parentElement;
      if (!el || !n.textContent?.trim() || el.closest('.visually-hidden, [aria-hidden="true"]')) continue;
      if (parseFloat(getComputedStyle(el).fontSize) < 16.995) out.push(n.textContent.trim().slice(0, 30));
    }
    return out;
  });
  expect(small).toEqual([]);
  expect(await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth)).toBe(
    0,
  );
  const result = await new AxeBuilder({ page } as unknown as ConstructorParameters<typeof AxeBuilder>[0])
    .include('#card-cc1-own-form')
    .withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa', 'wcag22aa'])
    .analyze();
  expect(result.violations.map((v) => `${v.id}: ${v.nodes.map((n) => n.target.join(' ')).join(' | ')}`)).toEqual([]);
});

// review of PR #66: the router applies a URL change in a React transition, so on a slow phone the second entry was
// built from a URL that still lacked the first and dropped it; both entries must stay
test('T31 two quick entries on a slow phone both stay in the fragment and the result', async ({ page }) => {
  const cdp = await page.context().newCDPSession(page);
  await cdp.send('Emulation.setCPUThrottlingRate', { rate: 6 });
  await page.goto(PLANS_URL);
  const card = await typeNumbers(page);
  await expect(card.getByTestId('card-cc1-own')).toContainText('97.917 nghìn đồng/ha');
  await expect(page).toHaveURL(new RegExp(`yp[.]cc1_spring_peanut=${PRICE}`));
  await expect(page).toHaveURL(new RegExp(`yc[.]cc1_spring_peanut=${COST}`));
});

// privacy review of PR #66: a crafted link with 200,000-digit values froze the cards for about a minute
test('T31 a link with a 200,000-digit price opens the cards promptly and does not use it', async ({ page }) => {
  await page.goto(`${PLANS_URL}&yp.cc1_spring_peanut=${'9'.repeat(200_000)}`);
  const card = page.locator('#the-cc1');
  await expect(card).toBeVisible({ timeout: 10_000 });
  await card.getByRole('button', { name: 'Tính với giá bán và chi phí của bạn' }).click({ timeout: 5_000 });
  await expect(card.getByRole('spinbutton', { name: /^Lạc.*Giá bán của bạn/ })).toHaveValue('');
  await expect(card.getByTestId('card-cc1-own')).toContainText('Nhập giá bán để tính.');
});
