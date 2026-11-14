import { test } from '@playwright/test';

// Field-phone profile: 4x CPU slowdown, slow 4G (1.6 Mbps, 150 ms), no cache. Median of 3 cold loads per page.
test('field-phone performance: LCP and CLS', async ({ page }, info) => {
  test.skip(info.project.name !== 'phone-360', 'phone only');
  test.setTimeout(180_000);
  const cdp = await page.context().newCDPSession(page);
  await cdp.send('Emulation.setCPUThrottlingRate', { rate: 4 });
  await cdp.send('Network.enable');
  await cdp.send('Network.setCacheDisabled', { cacheDisabled: true });
  await cdp.send('Network.emulateNetworkConditions', { offline: false, latency: 150, downloadThroughput: (1.6 * 1024 * 1024) / 8, uploadThroughput: (750 * 1024) / 8 });
  await page.goto('/#/'); // warm the local server once
  const lines: string[] = [];
  for (const url of ['/#/', '/#/nong-dan/ruong', '/#/nong-dan/phuong-an?ruong=canal_end&nam=2010,2020', '/#/khoa-hoc', '/#/bang-chung', '/#/tro-ly']) {
    const lcps: number[] = [];
    let cls = 0;
    for (let i = 0; i < 3; i++) {
      await page.goto('about:blank');
      await page.goto(url, { waitUntil: 'load' });
      await page.waitForTimeout(3500);
      const m = await page.evaluate(() => new Promise<{ lcp: number; cls: number }>((resolve) => {
        let lcp = 0; let c = 0;
        new PerformanceObserver((l) => { for (const e of l.getEntries()) lcp = Math.max(lcp, e.startTime); }).observe({ type: 'largest-contentful-paint', buffered: true });
        new PerformanceObserver((l) => { for (const e of l.getEntries() as (PerformanceEntry & { value: number; hadRecentInput: boolean })[]) if (!e.hadRecentInput) c += e.value; }).observe({ type: 'layout-shift', buffered: true });
        setTimeout(() => resolve({ lcp, cls: c }), 300);
      }));
      lcps.push(m.lcp);
      cls = Math.max(cls, m.cls);
    }
    lcps.sort((a, b) => a - b);
    lines.push(`${url} LCP median=${Math.round(lcps[1] ?? 0)}ms (${lcps.map(Math.round).join('/')}) CLS max=${cls.toFixed(3)}`);
  }
  console.log(`PERF\n${lines.join('\n')}`);
});
