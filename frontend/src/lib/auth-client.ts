export async function authMutation(action: 'register' | 'login' | 'logout' | 'forgot-password' | 'reset-password' | 'verify-email' | 'resend-verification', data?: Record<string, string>) {
  const csrf = await fetch('/api/auth/csrf', { cache: 'no-store', signal: AbortSignal.timeout(10000) });
  if (!csrf.ok) throw new Error('Не удалось подключиться. Попробуйте ещё раз.');
  const { token } = await csrf.json();
  const response = await fetch(`/api/auth/${action}`, {
    method: 'POST', headers: { 'Content-Type': 'application/json', 'X-CSRF-Token': token },
    body: JSON.stringify(data ?? {}), signal: AbortSignal.timeout(15000),
  });
  if (!response.ok) {
    const result = await response.json().catch(() => null);
    throw new Error(typeof result?.detail === 'string' ? result.detail : 'Проверьте заполнение полей и повторите.');
  }
}
