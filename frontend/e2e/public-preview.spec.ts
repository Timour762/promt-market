import { test, expect } from '@playwright/test';

test('standalone showcase works with no backend, keeps the hero and renders the public catalog', async ({ page, request }) => {
  const ready = await request.get('/api/ready');
  expect(await ready.json()).toEqual({ status: 'ready', mode: 'public_preview' });
  await page.goto('/');
  await expect(page.getByRole('link', { name: 'Витрина', exact: true })).toBeVisible();
  await expect(page.locator('.pv-collection,.pv-how,.launch-note,.store-footer')).toHaveCount(0);
  await expect(page.getByRole('link', { name: 'Войти', exact: true })).toHaveCount(0);
  await page.getByRole('link', { name: 'Найти свой промпт' }).click();
  await expect(page.locator('.pv-card')).toHaveCount(6);
  await page.getByRole('textbox', { name: 'Найти промпт' }).fill('Бизнес');
  await expect(page.locator('.pv-card')).toHaveCount(1);
  await page.getByRole('link', { name: 'Бизнес-план за 30 минут', exact: true }).click();
  await expect(page.getByRole('heading', { name: 'Бизнес-план за 30 минут', exact: true })).toBeVisible();
  await expect(page.locator('.store-product-price')).toContainText('500,00');
  await expect(page.getByRole('link', { name: 'Покупки скоро откроются' })).toBeVisible();
  await expect(page.getByRole('button', { name: /Купить|Оплатить|Заказать/ })).toHaveCount(0);
  await expect.poll(() => page.locator('.pv-product-image img').evaluateAll(images => images.every(image => (image as HTMLImageElement).naturalWidth > 0))).toBe(true);
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= document.documentElement.clientWidth + 1)).toBe(true);
  await page.getByRole('link', { name: 'Покупки скоро откроются' }).click();
  await expect(page.getByRole('heading', { name: 'Готовимся к запуску' })).toBeVisible();
});

test('private pages and all mutations are disabled even by direct requests', async ({ request }) => {
  for (const path of ['/login', '/register', '/forgot-password', '/reset-password', '/verify-email', '/account', '/account/library/business', '/account/orders/any/payment', '/admin', '/admin/orders', '/payment-preview', '/design-preview']) {
    const response = await request.get(path, { maxRedirects: 0 });
    expect(response.status(), path).toBe(307);
    expect(response.headers().location, path).toBe('https://showcase.example.test/preview');
    expect(response.headers()['set-cookie'], path).toBeUndefined();
  }
  const forwarded = await request.get('/login', { maxRedirects: 0, headers: { 'x-forwarded-host': 'untrusted.example.test', 'x-forwarded-proto': 'http' } });
  expect(forwarded.headers().location).toBe('https://showcase.example.test/preview');
  for (const path of ['/api/auth/csrf', '/api/auth/me', '/api/library/any/download', '/api/admin/orders', '/api/orders', '/api/payments/any/status']) {
    const response = await request.get(path);
    expect(response.status(), path).toBe(404);
    expect(await response.json()).toEqual({ error: 'not_available_in_preview' });
    expect(response.headers()['set-cookie'], path).toBeUndefined();
  }
  for (const method of ['POST', 'PUT', 'PATCH', 'DELETE']) {
    for (const path of ['/', '/api/auth/register', '/api/orders', '/api/payments/platega/webhook', '/api/admin/payments/any/confirm']) {
      const response = await request.fetch(path, { method, data: { email: 'unused@example.test' } });
      expect(response.status(), `${method} ${path}`).toBe(503);
      expect(await response.json()).toEqual({ error: 'public_preview_read_only' });
      expect(response.headers()['set-cookie']).toBeUndefined();
    }
  }
});

test('public HTML and documents describe the showcase without account cookies', async ({ request }) => {
  for (const path of ['/', '/catalog', '/catalog/collection', '/pricing', '/prompts/python', '/prompts/business', '/legal/privacy', '/legal/terms', '/legal/offer', '/legal/contacts']) {
    const response = await request.get(path, { headers: { Cookie: 'pm_session=unused-preview-session' } });
    expect(response.status(), path).toBe(200);
    expect(response.headers()['x-robots-tag']).toBe('noindex, nofollow');
    expect(response.headers()['set-cookie']).toBeUndefined();
    const html = await response.text();
    expect(html).not.toContain('href="/login');
    expect(html).not.toContain('href="/account');
  }
  const privacy = await request.get('/legal/privacy');
  expect(await privacy.text()).toContain('Витрина не обращается к базе аккаунтов и заказов');
  expect((await request.head('/api/ready')).status()).toBe(200);
  expect((await request.get('/prompts/no-such-prompt')).status()).toBe(404);
});

test('documents, direct support and itemized prices are reachable without an account', async ({ page }) => {
  await page.goto('/');
  await page.getByRole('link', { name: 'Цены и тарифы', exact: true }).click();
  await expect(page.getByRole('heading', { name: 'Цены и тарифы', exact: true })).toBeVisible();
  await expect(page.locator('.pricing-table tbody tr')).toHaveCount(6);
  for (const row of await page.locator('.pricing-table tbody tr').all()) {
    await expect(row.locator('td').last()).toContainText('500');
    await expect(row.locator('td').last()).toContainText('однократно');
  }
  await expect(page.locator('.pricing-facts')).toContainText('Без подписки и автосписаний');
  await expect(page.locator('.pricing-status')).toContainText('Реальная оплата пока отключена');
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= document.documentElement.clientWidth + 1)).toBe(true);
  await page.locator('.pricing-support').getByRole('link', { name: 'Пользовательское соглашение' }).click();
  await expect(page.getByRole('heading', { name: 'Пользовательское соглашение', exact: true })).toBeVisible();
  await expect(page.locator('time')).toHaveAttribute('dateTime', '2026-10-23');
  await expect(page.locator('.legal-draft')).toHaveCount(0);
  await page.locator('.legal-nav').getByRole('link', { name: 'Политика конфиденциальности', exact: true }).click();
  await expect(page.locator('.legal-page')).toContainText('Эскиев Тимур Бухариевич');
  await expect(page.locator('.legal-draft')).toHaveCount(0);
  await page.locator('.legal-nav').getByRole('link', { name: 'Контакты поддержки' }).click();
  await expect(page.locator('.support-contact').getByRole('link', { name: 'promtmarket@mail.ru' })).toHaveAttribute('href', 'mailto:promtmarket@mail.ru');
  await page.locator('.legal-nav').getByRole('link', { name: 'Условия приобретения промптов' }).click();
  await expect(page.locator('.legal-draft')).toContainText('для согласования');
});
