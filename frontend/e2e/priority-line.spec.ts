import { expect, test, type Page } from '@playwright/test';

const plansUrl = (priority: string) => `/#/nong-dan/phuong-an?ruong=canal_end&nam=2010,2020&uutien=${priority}`;
const TESTED = ['cc1', 'cc2', 'cc3', 'cc4'];
// UI-UX-SPEC T37 and D-136: never better, best, should or recommended, nor their Vietnamese equivalents (glossary)
const BANNED =
  /better|best|should|recommend|propos|suitable|more profitable|tốt hơn|tốt nhất|\bnên\b|khuyến nghị|khuyên|đề xuất|đề nghị|phù hợp|lãi hơn/i;
const ROW = { income: 'money', stability: 'weather', water: 'water', land: 'land' } as const;

const values = (page: Page, selector: string) =>
  page.locator(selector).evaluateAll((els) => els.map((e) => e.getAttribute('data-value')));

test('T37 priority-line the line is on cc1..cc4 only, inside the highlighted row, with the usual card values', async ({
  page,
}) => {
  for (const priority of ['income', 'stability', 'water', 'land'] as const) {
    await page.goto(plansUrl(priority));
    await expect(page.locator('article[id^="the-"]')).toHaveCount(6);
    for (const id of TESTED) {
      const line = page.getByTestId(`card-${id}-priority-line`);
      await expect(line).toHaveCount(1);
      const row = page.locator(`[data-testid="card-${id}-row-${ROW[priority]}"][data-highlighted="true"]`);
      await expect(row.getByTestId(`card-${id}-priority-line`)).toHaveCount(1);
      expect(await line.textContent()).not.toMatch(BANNED);
      // the P-02 short source name, not the author line P-02 shares with P-03
      await expect(line).toContainText('Trịnh Đức Toàn và cs. 2023 · VAAS');
    }
    await expect(page.locator('[data-testid="card-usual"] [data-testid$="-priority-line"]')).toHaveCount(0);
    await expect(page.locator('[data-testid="card-usual_p03"] [data-testid$="-priority-line"]')).toHaveCount(0);
  }

  // income: this card's money total and the usual card's, as their rows show them
  await page.goto(plansUrl('income'));
  await expect(page.locator('article[id^="the-"]')).toHaveCount(6);
  const total = (id: string) =>
    // the money total is the first block of the row's fold (D-187 item 4)
    values(page, `[id="card-${id}-row-money-body"] > div:not([data-testid]) [data-value]`);
  const usualTotal = await total('usual');
  expect(usualTotal).toHaveLength(1);
  for (const id of TESTED) {
    const own = await total(id);
    expect(await values(page, `[data-testid="card-${id}-priority-line"] [data-value]`)).toEqual([
      ...own,
      ...usualTotal,
    ]);
  }

  // land: crops in the year and living days, this card's then the usual card's
  await page.goto(plansUrl('land'));
  await expect(page.locator('article[id^="the-"]')).toHaveCount(6);
  // the first source button of the crops line and of the living-days line; the rest open the land-care principles
  const landValues = async (id: string) =>
    await values(page, `[data-testid="card-${id}-row-land"] ul > li:nth-child(-n+2) [data-value]:first-of-type`);
  const usualLand = await landValues('usual');
  expect(usualLand).toHaveLength(2);
  for (const id of TESTED) {
    const own = await landValues(id);
    expect(await values(page, `[data-testid="card-${id}-priority-line"] [data-value]`)).toEqual([
      own[0],
      usualLand[0],
      own[1],
      usualLand[1],
    ]);
  }
});

test('T3 changing the priority in the link with the same response changes only the highlight and the priority line', async ({
  page,
}) => {
  // the app checks the request echo of every response (api.ts), so the new priority asks again; the test records each
  // response to show that it is the same apart from that echo
  const bodies: Record<string, unknown>[] = [];
  await page.route('**/api/compare', async (route) => {
    const response = await route.fetch();
    bodies.push((await response.json()) as Record<string, unknown>);
    await route.fulfill({ response });
  });
  const rows = () =>
    page.locator('[data-testid^="card-"][data-testid*="-row-"]').evaluateAll((els) =>
      els.map((e) => {
        const line = e.querySelector('[data-testid$="-priority-line"]')?.textContent ?? '';
        // the "your priority" tag under the title in the row's heading button (D-187 item 4)
        const label = e.querySelector('h3 > button > span > span')?.textContent ?? '';
        return {
          hook: e.getAttribute('data-testid'),
          highlighted: e.getAttribute('data-highlighted') === 'true',
          text: (e.textContent ?? '').replace(line, '').replace(label, ''),
        };
      }),
    );
  const lines = () => page.locator('[data-testid$="-priority-line"]').allTextContents();
  const order = () => page.locator('article[id^="the-"]').evaluateAll((els) => els.map((e) => e.id));

  await page.goto(plansUrl('income'));
  await expect(page.locator('article[id^="the-"]')).toHaveCount(6);
  const before = { rows: await rows(), lines: await lines(), order: await order() };

  await page.evaluate(() => {
    window.location.hash = window.location.hash.replace('uutien=income', 'uutien=land');
  });
  await expect(page.locator('[data-testid="card-cc1-row-land"]')).toHaveAttribute('data-highlighted', 'true');
  const after = { rows: await rows(), lines: await lines(), order: await order() };

  expect(bodies).toHaveLength(2);
  const [a, b] = bodies.map(({ request, ...rest }) => [request, rest]);
  expect(b?.[1]).toEqual(a?.[1]);
  expect(after.order).toEqual(before.order);
  expect(after.rows.map((r) => [r.hook, r.text])).toEqual(before.rows.map((r) => [r.hook, r.text]));
  const marked = (r: typeof before.rows) => r.filter((x) => x.highlighted).map((x) => x.hook);
  expect(marked(before.rows)).toEqual(before.order.map((id) => `card-${id.slice(4)}-row-money`));
  expect(marked(after.rows)).toEqual(before.order.map((id) => `card-${id.slice(4)}-row-land`));
  expect(after.lines).toHaveLength(4);
  expect(after.lines).not.toEqual(before.lines);
});
