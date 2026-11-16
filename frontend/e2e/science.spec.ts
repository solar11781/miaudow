import { expect, test } from '@playwright/test';

// visual audit 2026-11-16: the source button under the grid table started left of the table's text
test('the source under the grid table starts where the table text starts', async ({ page }) => {
  await page.goto('/#/khoa-hoc');
  const wrap = page.locator('[class*="tableWrap"]');
  await expect(wrap.locator('tbody tr')).toHaveCount(5);
  const left = await wrap.evaluate((w) => {
    const textLeft = (el: Element | null) => {
      const range = document.createRange();
      range.selectNodeContents(el as Element);
      return range.getBoundingClientRect().left;
    };
    return {
      cell: textLeft(w.querySelector('tbody th')),
      source: textLeft(w.querySelector('button [class*="figure"]')),
    };
  });
  expect(Math.abs(left.source - left.cell)).toBeLessThanOrEqual(1);
});

// visual audit 2026-11-16: the greenness line was dark green on the dark card. WCAG 1.4.11: a chart line or bar
// needs 3:1 against what is behind it, in both themes.
for (const colorScheme of ['dark', 'light'] as const) {
  test(`every chart line and bar of the data room has 3:1 contrast in the ${colorScheme} theme`, async ({ page }) => {
    await page.emulateMedia({ colorScheme });
    await page.goto('/#/khoa-hoc');
    await expect(page.locator('main svg polyline').first()).toBeAttached();
    const low = await page.locator('main').evaluate((main) => {
      const canvas = document.createElement('canvas');
      canvas.width = canvas.height = 1;
      const ctx = canvas.getContext('2d', { willReadFrequently: true }) as CanvasRenderingContext2D;
      const rgba = (colour: string) => {
        ctx.clearRect(0, 0, 1, 1);
        ctx.fillStyle = colour;
        ctx.fillRect(0, 0, 1, 1);
        const d = ctx.getImageData(0, 0, 1, 1).data;
        return [d[0] ?? 0, d[1] ?? 0, d[2] ?? 0, (d[3] ?? 0) / 255];
      };
      const behind = (el: Element | null): number[] => {
        for (let e = el; e; e = e.parentElement) {
          const c = rgba(getComputedStyle(e).backgroundColor);
          if ((c[3] ?? 0) > 0.9) return c;
        }
        return [255, 255, 255, 1];
      };
      const luminance = (c: number[]) => {
        const [r = 0, g = 0, b = 0] = c.map((v) =>
          v / 255 <= 0.03928 ? v / 255 / 12.92 : ((v / 255 + 0.055) / 1.055) ** 2.4,
        );
        return 0.2126 * r + 0.7152 * g + 0.0722 * b;
      };
      const marks = main.querySelectorAll(
        'svg polyline, svg line[stroke^="var(--"], svg circle[stroke^="var(--"], svg rect[rx][fill^="var(--"]',
      );
      const found = new Set<string>();
      for (const mark of marks) {
        const style = getComputedStyle(mark);
        const paint = rgba(mark.tagName === 'rect' ? style.fill : style.stroke);
        const bg = behind(mark.closest('svg'));
        const alpha = Number(style.opacity) * (paint[3] ?? 1);
        const seen = paint.slice(0, 3).map((v, i) => v * alpha + (bg[i] ?? 0) * (1 - alpha));
        const [hi, lo] = [luminance(seen), luminance(bg)].sort((a, b) => b - a);
        const ratio = ((hi ?? 0) + 0.05) / ((lo ?? 0) + 0.05);
        const name = mark.closest('svg')?.querySelector('title')?.textContent;
        if (ratio < 3) found.add(`${name}: ${mark.tagName} ${style.opacity} ${ratio.toFixed(2)}`);
      }
      return [...found];
    });
    expect(low).toEqual([]);
  });
}
