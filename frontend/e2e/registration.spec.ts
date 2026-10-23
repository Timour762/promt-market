import { randomBytes } from 'node:crypto';
import { test, expect } from '@playwright/test';

test('register, open the private account, log out and sign in again without sending mail', async ({ page, context }, testInfo) => {
  const email = `browser-${testInfo.project.name}-${randomBytes(6).toString('hex')}@example.com`;
  const password = randomBytes(24).toString('base64url');
  const name = `Покупатель ${testInfo.project.name}`;

  await page.goto('/register');
  await expect(page.getByRole('heading', { name: 'Ваш аккаунт в ПромтМаркете' })).toBeVisible();
  await expect(page.locator('.auth-page')).not.toContainText('Локальная версия');
  await expect(page.getByRole('link', { name: 'политикой конфиденциальности', exact: true })).toHaveAttribute('href', '/legal/privacy');
  await page.getByLabel('Ваше имя').fill(name);
  await page.getByLabel('Email', { exact: true }).fill(email);
  await page.getByLabel('Пароль', { exact: true }).fill(password);
  await page.getByLabel('Повторите пароль').fill(password);
  const registration = page.waitForResponse(response => response.url().endsWith('/api/auth/register') && response.request().method() === 'POST');
  await page.getByRole('button', { name: 'Создать аккаунт' }).click();
  const response = await registration;
  expect(response.status()).toBe(201);
  await expect(page).toHaveURL(/\/account$/);
  await expect(page.getByRole('heading', { name: 'Ваш профиль', exact: true })).toBeVisible();
  await expect(page.locator('.profile-section')).toContainText(email);
  await expect(page.locator('.verification-notice')).not.toContainText('.local/mail');
  await expect(page.getByRole('link', { name: 'Управление магазином' })).toHaveCount(0);

  const session = (await context.cookies()).find(cookie => cookie.name === 'pm_session');
  expect(session?.httpOnly).toBe(true);
  expect(session?.sameSite).toBe('Lax');
  await page.reload();
  await expect(page.locator('.profile-section')).toContainText(email);

  const state = await page.request.get(`http://127.0.0.1:8137/__auth_test_state?email=${encodeURIComponent(email)}`);
  expect(await state.json()).toMatchObject({
    exists: true, role: 'customer', password_hashed: true, sessions: 1,
    verification_tokens: 1, outbox_encrypted: true, delivered_messages: 0,
  });

  await page.getByRole('button', { name: 'Выйти из аккаунта' }).click();
  await expect(page).toHaveURL(/\/login$/);
  expect((await context.cookies()).find(cookie => cookie.name === 'pm_session')).toBeUndefined();
  await page.goto('/account');
  await expect(page).toHaveURL(/\/login$/);
  await page.getByLabel('Логин или email').fill(email);
  await page.getByLabel('Пароль', { exact: true }).fill(password);
  await page.getByRole('button', { name: 'Войти', exact: true }).click();
  await expect(page).toHaveURL(/\/account$/);
  await expect(page.locator('.profile-section')).toContainText(email);
});

test('production recovery and forms stay safe without JavaScript or hydrated handlers', async ({ page, browser }) => {
  const noJavaScript = await browser.newContext({ javaScriptEnabled: false });
  try {
    const unhydratedPage = await noJavaScript.newPage();
    for (const path of ['/login', '/register', '/forgot-password']) {
      await unhydratedPage.goto(`http://127.0.0.1:3137${path}`);
      const form = unhydratedPage.locator('.auth-form');
      await expect(form).toHaveAttribute('method', 'post');
      await expect(form.locator('button[type="submit"]')).toBeDisabled();
      for (const input of await form.locator('input').all()) await expect(input).toBeDisabled();
      expect(new URL(unhydratedPage.url()).search).toBe('');
    }
  } finally {
    await noJavaScript.close();
  }
  await page.goto('/forgot-password');
  await page.getByLabel('Email аккаунта').fill(`unknown-${randomBytes(6).toString('hex')}@example.com`);
  await page.getByRole('button', { name: 'Подготовить письмо' }).click();
  await expect(page.getByRole('heading', { name: 'Запрос на восстановление принят' })).toBeVisible();
  await expect(page.getByRole('status')).toContainText('Если аккаунт с таким email существует');
  await expect(page.getByRole('status')).not.toContainText('.local/mail');
  for (const path of ['/verify-email', '/reset-password']) {
    await page.goto(path);
    await expect(page.getByRole('heading', { name: 'Нужна ссылка из письма' })).toBeVisible();
    await expect(page.locator('.auth-page')).not.toContainText('Локальный режим');
  }
});
