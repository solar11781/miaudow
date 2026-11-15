import { expect, test } from '@playwright/test';
import { vi } from '../src/i18n/vi';

// D-187 (roleplay audit 2026-11-15, F2): the source notes move from the cards into the source sheets; the card keeps
// its warnings (H17), the statistics office credit in the rice block (UI-UX-SPEC 12b) and the soil model label
const PLANS_URL = '/#/nong-dan/phuong-an?ruong=water_short&nam=2010&uutien=income';
const IDS = ['usual', 'usual_p03', 'cc1', 'cc2', 'cc3', 'cc4'];

test('T16 card-warnings each card shows its warnings, and the rice and soil labels stay visible', async ({ page }) => {
  await page.goto(PLANS_URL);
  await expect(page.locator('article[id^="the-"]')).toHaveCount(6);
  for (const id of IDS) {
    const card = page.getByTestId(`card-${id}`);
    for (const line of [vi.farmer.trialNote, vi.farmer.priceYear('2020-21'), vi.common.notForecast, vi.common.support])
      await expect(card.getByText(line, { exact: true }), `${id}: ${line}`).toBeVisible();
    // the money row's heading: profit in the trial, not on the farmer's field (CLAUDE.md: revenue is not profit)
    const heading = page.getByTestId(`card-${id}-row-money`).locator('h3');
    await expect(heading, id).toBeVisible();
    await expect(heading, id).toContainText(vi.farmer.rows.money);
  }
  // the two rice cards: the credit sits inside the rice block of the weather row
  for (const id of ['usual', 'usual_p03']) {
    const rice = page.getByTestId(`card-${id}-row-weather`);
    await expect(rice.getByText(vi.farmer.rice.nsoCredit, { exact: true }), id).toBeVisible();
  }
  for (const id of ['usual', 'cc1', 'cc2', 'cc3', 'cc4']) {
    const water = page.getByTestId(`card-${id}-row-water`);
    await expect(water.getByText(vi.farmer.rows.soilNote, { exact: true }), id).toBeVisible();
  }
});

test('D-187 a note that left the card opens in the source sheet of its number', async ({ page }) => {
  await page.goto(PLANS_URL);
  const money = page.getByTestId('card-cc1-row-money');
  await expect(money).not.toContainText('Bảng 13');
  await expect(money).not.toContainText('RVAC');
  await money.locator('ul [data-value]').first().click();
  const sheet = page.getByTestId('source-sheet');
  await expect(sheet).toBeVisible();
  await expect(sheet).toContainText(vi.farmer.profitTable);
  await expect(sheet).toContainText('RVAC');
  await page.keyboard.press('Escape');
  await expect(sheet).toBeHidden();
});

// D-187 (F4): each risk quote is one plain line on the card; the full quote opens with the line's source button
test('D-187 a consideration is one plain line and its quote opens in the source sheet', async ({ page }) => {
  await page.goto(PLANS_URL);
  const checks = page.getByTestId('card-cc1-row-checks');
  const cost = checks.locator('li', { hasText: vi.farmer.considerations.cost.line });
  await expect(cost).toBeVisible();
  await expect(checks).not.toContainText('Thị trường tiêu thụ nhỏ hẹp');
  await cost.getByRole('button').click();
  const sheet = page.getByTestId('source-sheet');
  await expect(sheet).toContainText(vi.sheet.quote);
  await expect(sheet).toContainText(
    'Tổng chi phí trồng lạc và ớt chỉ thiên F1 thường cao gấp 2 - 3 lần so với trồng lúa.',
  );
});
