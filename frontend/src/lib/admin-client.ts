import type { AdminPrompt } from './admin-types';
export async function adminMutation<T = AdminPrompt>(path: string, method: 'POST' | 'PATCH', data: unknown): Promise<T> {
  const csrf = await fetch('/api/auth/csrf', { cache: 'no-store', signal: AbortSignal.timeout(10000) });
  if (!csrf.ok) throw new Error('Не удалось подготовить запрос. Повторите попытку.');
  const { token } = await csrf.json();
  const response = await fetch(`/api/admin/${path}`, { method, headers: { 'Content-Type': 'application/json', 'X-CSRF-Token': token }, body: JSON.stringify(data), signal: AbortSignal.timeout(15000) });
  if (!response.ok) {
    const body = await response.json().catch(() => null);
    throw new Error(typeof body?.detail === 'string' ? body.detail : response.status === 401 ? 'Сессия завершилась. Скопируйте правки и войдите снова.' : 'Проверьте поля и повторите сохранение.');
  }
  return response.json();
}
