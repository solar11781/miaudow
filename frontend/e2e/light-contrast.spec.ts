import { expect, test, type Locator } from '@playwright/test';
import { vi } from '../src/i18n/vi';

// visual audit 2026-11-16: pale gold on the light theme's paper. H8: text at least 4.5:1, icons at least 3:1 (WCAG AA).
test.use({ colorScheme: 'light' });

/** Contrast of an element's colour against the solid backgrounds painted behind it (WCAG relative luminance). */
const contrast = (part: Locator) =>
  part.evaluate((el) => {
    const canvas = document.createElement('canvas');
    canvas.width = canvas.height = 1;
    const pen = canvas.getContext('2d');
    if (!pen) return 0;
    const pixel = () => [...pen.getImageData(0, 0, 1, 1).data].slice(0, 3);
    const paint = (colour: string) => {
      pen.fillStyle = colour;
      pen.fillRect(0, 0, 1, 1);
    };
    const chain: Element[] = [];
    for (let node: Element | null = el; node; node = node.parentElement) chain.unshift(node);
    paint('#fff');
    for (const node of chain) paint(getComputedStyle(node).backgroundColor);
    const behind = pixel();
    paint(getComputedStyle(el).color);
    const ink = pixel();
    const luminance = (rgb: number[]) => {
      const [r = 0, g = 0, b = 0] = rgb.map((v) => {
        const c = v / 255;
        return c <= 0.04045 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4;
      });
      return 0.2126 * r + 0.7152 * g + 0.0722 * b;
    };
    const [dark, light] = [luminance(ink), luminance(behind)].sort((a, b) => a - b);
    return ((light ?? 0) + 0.05) / ((dark ?? 0) + 0.05);
  });

test('H8 the start page step labels and help icons read on the light theme', async ({ page }) => {
  await page.goto('/#/nong-dan');
  const steps = page.getByRole('list', { name: vi.farmer.stepsLabel });
  for (const n of [1, 2, 3, 4])
    expect(await contrast(steps.getByText(vi.home.stepLabel(n), { exact: true })), `step ${n}`).toBeGreaterThanOrEqual(
      4.5,
    );
  const helps = page.getByRole('region', { name: vi.farmer.helpsTitle }).locator('ul').first();
  for (const icon of await helps.locator('li > span:has(svg)').all())
    expect(await contrast(icon)).toBeGreaterThanOrEqual(3);
});

test('the priority tile icons read on the light theme, chosen or not', async ({ page }) => {
  await page.goto('/#/nong-dan/uu-tien?ruong=water_short&nam=2010');
  const tiles = page.getByRole('radio');
  await expect(tiles).toHaveCount(4);
  await tiles.first().click();
  for (const tile of await tiles.all())
    expect(await contrast(tile.locator('span:has(svg)').first())).toBeGreaterThanOrEqual(3);
});
