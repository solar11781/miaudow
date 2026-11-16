import { expect, test } from '@playwright/test';

// member A, 2026-11-16: the question box was pinned to the bottom of the window, so while the page scrolled it floated
// over the example questions and the mode switch of its own panel
test('the question box sits at the end of its panel and never covers the example questions', async ({ page }) => {
  await page.goto('/#/tro-ly');
  const form = page.getByRole('main').locator('form');
  const examples = page.getByLabel('Câu hỏi mẫu');
  await expect(form).toBeVisible();
  await expect(examples).toBeVisible();
  for (const y of [0, 200, 400, 600]) {
    await page.evaluate((top) => window.scrollTo(0, top), y);
    const [f, e] = await Promise.all([form.boundingBox(), examples.boundingBox()]);
    expect(f && e && f.y >= e.y + e.height, `scrolled ${y} px`).toBe(true);
  }
});

// roleplay audit 2026-11-16: on a phone the chat is the task, so the explanation comes after it
test('the example questions come before the explanation of how the assistant works', async ({ page }) => {
  test.skip((page.viewportSize()?.width ?? 0) > 960, 'wide screens keep two columns, explanation on the left');
  await page.goto('/#/tro-ly');
  const examples = await page.getByLabel('Câu hỏi mẫu').boundingBox();
  const explanation = await page.getByRole('heading', { name: /Hỏi bằng lời của mình/ }).boundingBox();
  expect(examples && explanation && examples.y < explanation.y).toBe(true);
});

test('the first example question leads on to the comparison with the field type it names', async ({ page }) => {
  await page.goto('/#/tro-ly');
  await page.getByLabel('Câu hỏi mẫu').getByRole('button').first().click();
  const link = page.getByRole('link', { name: /So sánh các cách trồng cho/ });
  await expect(link).toHaveAttribute('href', '#/nong-dan/nam?ruong=canal_end');
  await link.click();
  await expect(page).toHaveURL(/nong-dan\/nam\?ruong=canal_end/);
});
