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

// visual audit 2026-11-16: the globe page named its cells "19.0°N 105.625°E" in Vietnamese too; a cell is named the
// same way on every page (north is "B", east is "Đ", decimal comma)
test('the globe page names a grid cell in the reading language', async ({ page }) => {
  await page.goto('/#/dai-quan-sat?canh=insight');
  const cells = page.getByRole('group', { name: 'Chọn ô lưới' });
  await expect(cells.getByRole('radio', { name: '19,0°B 105,625°Đ', exact: true })).toBeVisible();
  await expect(cells).not.toContainText('°N');
});

// visual audit 2026-11-16: on the flat map the trial site's name ran out of the frame on a phone and lay under a
// cell button
test('the flat map keeps its place names inside the frame and over the cells', async ({ page }) => {
  await page.setViewportSize({ width: 360, height: 740 });
  await page.goto('/#/khoa-hoc');
  const flat = page.getByRole('button', { name: '2D', exact: true });
  const toggle = page.getByRole('button', { name: 'Địa hình (NASA SRTM)' });
  await flat.or(toggle).first().waitFor();
  if (await flat.isVisible()) await flat.click();
  await toggle.waitFor();
  const names = page.locator('g[class*="place"] text');
  await expect(names).toHaveCount(2);
  // retried: the map takes half a second to lie flat after the 2D button
  await expect(async () => {
    const frame = await page.locator('svg[class*="plane"] rect[class*="base"]').first().boundingBox();
    for (const box of await names.evaluateAll((els) => els.map((e) => e.getBoundingClientRect()))) {
      expect(box.left).toBeGreaterThanOrEqual((frame?.x ?? 0) - 1);
      expect(box.right).toBeLessThanOrEqual((frame?.x ?? 0) + (frame?.width ?? 0) + 1);
    }
  }).toPass({ timeout: 5000 });
  // drawn after the cell buttons, so a cell never covers a name
  const after = await names.first().evaluate((el) => {
    const cells = [...document.querySelectorAll('button[aria-pressed][class*="prism"]')];
    const last = cells[cells.length - 1];
    return Boolean(last && last.compareDocumentPosition(el) & Node.DOCUMENT_POSITION_FOLLOWING);
  });
  expect(after).toBe(true);
});

// roleplay audit 2026-11-16 (official): the cell table's "Đo được" column gave bare numbers with no unit
test('the cell table names the unit of its measured column', async ({ page }) => {
  await page.goto('/#/khoa-hoc');
  const table = page.getByRole('table', { name: /Bảng số liệu các ô lưới/ });
  await expect(table.getByRole('columnheader', { name: /^Đo được \(.+\)$/ })).toBeVisible();
});
