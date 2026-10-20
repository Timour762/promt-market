import { test, expect } from '@playwright/test';

test('Platega redirects to RUB checkout and opens the prompt only after server confirmation', async ({ page, context, browser }, testInfo) => {
  const origin = 'http://127.0.0.1:3117';
  await context.addCookies([{ name: 'pm_session', value: 'manual-e2e-' + testInfo.project.name, url: origin, httpOnly: true, sameSite: 'Lax' }]);
  const errors: string[] = [];
  page.on('pageerror', error => errors.push(error.message));
  await page.route('https://pay.platega.io/**', async route => {
    await route.fulfill({ contentType: 'text/html; charset=utf-8', body: '<html lang="ru"><meta charset="utf-8"><h1>Учебная страница Platega</h1><p>Это тест, деньги не списываются.</p></html>' });
  });
  await page.goto('/prompts/fixture-prompt');
  await page.getByRole('button', { name: 'Оформить заказ', exact: true }).click();
  await expect(page).toHaveURL(/\/account\/orders\/[0-9a-f-]+$/);
  const orderId = new URL(page.url()).pathname.split('/')[3];
  if (testInfo.project.name === 'desktop') {
    await expect(page.getByText('Ожидает оплаты', { exact: true })).toBeVisible();
    await page.goto(`${origin}/account/orders/${orderId}/payment`);
    await expect(page.getByRole('heading', { name: 'Оплата через Platega' })).toBeVisible();
    await expect(page.getByRole('heading', { name: 'Ожидаем подтверждение администратора' })).toHaveCount(0);
    await page.goto(`${origin}/account/orders/${orderId}`);
  }
  await expect(page.getByRole('heading', { name: 'Оплата через Platega' })).toBeVisible();
  await expect(page.getByRole('heading', { name: 'Ожидаем подтверждение администратора' })).toHaveCount(0);
  await expect(page.getByText('Реквизиты получателя', { exact: true })).toHaveCount(0);
  await page.getByRole('button', { name: 'Оплатить', exact: true }).click();
  await expect(page).toHaveURL(/^https:\/\/pay\.platega\.io\//);
  const transactionId = new URL(page.url()).searchParams.get('id');
  await expect(page.getByRole('heading', { name: 'Учебная страница Platega' })).toBeVisible();
  await page.goto(`${origin}/account/orders/${orderId}/payment`);
  await expect(page.getByRole('heading', { name: 'Ожидаем подтверждение Platega' })).toBeVisible();
  expect((await context.request.get(`/api/library/${orderId}/download`)).status()).toBe(404);
  await page.reload();
  await expect(page.getByRole('heading', { name: 'Ожидаем подтверждение Platega' })).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= document.documentElement.clientWidth + 1)).toBe(true);
  await page.screenshot({ path: `../.local/platega-${testInfo.project.name}.png`, fullPage: true });
  expect((await context.request.post(`http://127.0.0.1:8117/__test_confirm/${transactionId}`)).ok()).toBe(true);
  await expect(page.getByRole('heading', { name: 'Оплата подтверждена', exact: true })).toBeVisible({ timeout: 15000 });
  await page.getByRole('link', { name: 'Открыть промпт ↗' }).click();
  await expect(page.locator('.prompt-full-text')).toHaveText('PRIVATE_BROWSER_FIXTURE_CONTENT');

  const adminContext = await browser.newContext({ baseURL: origin, viewport: page.viewportSize() ?? undefined });
  try {
    await adminContext.addCookies([{ name: 'pm_session', value: 'manual-e2e-admin', url: origin, httpOnly: true, sameSite: 'Lax' }]);
    const admin = await adminContext.newPage();
    await admin.goto('/account');
    await expect(admin.getByRole('heading', { name: 'Platega · рубли и USDT' })).toBeVisible();
    await expect(admin.getByRole('heading', { name: 'Карта для получения оплаты' })).toHaveCount(0);
    await admin.goto('/admin/payments');
    await expect(admin.getByRole('heading', { name: 'Платежи · Platega' })).toBeVisible();
    const row = admin.locator('tbody tr').filter({ hasText: 'Fixture ' + testInfo.project.name });
    await expect(row).toContainText('Подтверждён');
    await expect(row).toContainText('5,5 USDT');
    expect(await admin.evaluate(() => document.documentElement.scrollWidth <= document.documentElement.clientWidth + 1)).toBe(true);
    await admin.screenshot({ path: `../.local/platega-admin-${testInfo.project.name}.png`, fullPage: true });
  } finally { await adminContext.close(); }
  expect(errors).toEqual([]);
});
