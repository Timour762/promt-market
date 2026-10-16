"use client";
import { useEffect, useState, type FormEvent } from 'react';
import { authMutation } from '../lib/auth-client';
type Mode = 'forgot-password' | 'reset-password' | 'verify-email';
export default function RecoveryForm({ mode }: { mode: Mode }) {
  const [token, setToken] = useState<string | null>(null);
  const [pending, setPending] = useState(false);
  const [done, setDone] = useState(false);
  const [error, setError] = useState('');
  useEffect(() => {
    if (mode !== 'forgot-password') setToken(new URLSearchParams(window.location.hash.slice(1)).get('token') ?? '');
  }, [mode]);
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); if (pending || done) return;
    const form = new FormData(event.currentTarget);
    const password = String(form.get('password') ?? '');
    if (mode === 'reset-password' && password !== form.get('confirm')) { setError('Пароли не совпадают'); return; }
    if (mode !== 'forgot-password' && !token) { setError('Откройте ссылку из письма.'); return; }
    setPending(true); setError('');
    try {
      await authMutation(mode, mode === 'forgot-password' ? { email: String(form.get('email') ?? '') } : { token: token!, ...(mode === 'reset-password' ? { password } : {}) });
      if (mode !== 'forgot-password') window.history.replaceState(null, '', window.location.pathname);
      setToken(''); setDone(true);
    } catch (cause) { setError(cause instanceof Error && cause.name !== 'TimeoutError' ? cause.message : 'Не удалось подключиться. Попробуйте ещё раз.'); }
    finally { setPending(false); }
  }
  if (done) return <section className="recovery-result" role="status"><h2>{mode === 'forgot-password' ? 'Запрос на восстановление принят' : mode === 'verify-email' ? 'Email подтверждён' : 'Пароль изменён'}</h2><p>{mode === 'forgot-password' ? 'Если аккаунт существует, письмо поставлено в очередь. При настроенной отправке оно придёт на email. В локальном режиме проверьте папку .local/mail.' : mode === 'verify-email' ? 'Адрес подтверждён. Можно вернуться в личный кабинет.' : 'Все прежние сеансы завершены. Войдите с новым паролем.'}</p><a className="primary" href={mode === 'verify-email' ? '/account' : '/login'}>{mode === 'verify-email' ? 'В личный кабинет' : 'Перейти ко входу'} ↗</a></section>;
  if (mode !== 'forgot-password' && token === null) return <p role="status">Открываем ссылку…</p>;
  if (mode !== 'forgot-password' && !token) return <section className="recovery-result"><h2>Нужна ссылка из письма</h2><p>{mode === 'verify-email' ? 'Запросите письмо в личном кабинете и откройте ссылку в нём.' : 'Запросите новое письмо для восстановления пароля.'}</p><a className="primary" href={mode === 'verify-email' ? '/account' : '/forgot-password'}>{mode === 'verify-email' ? 'В личный кабинет' : 'Запросить письмо'} ↗</a></section>;
  return <form className="auth-form" onSubmit={submit} aria-busy={pending}>
    {mode === 'forgot-password' && <label htmlFor="email">Email аккаунта<input id="email" name="email" type="email" required maxLength={254} autoComplete="email" disabled={pending}/></label>}
    {mode === 'reset-password' && <><label htmlFor="password">Новый пароль<input id="password" name="password" type="password" required minLength={12} maxLength={128} autoComplete="new-password" aria-describedby="password-hint" disabled={pending}/></label><p className="field-hint" id="password-hint">От 12 до 128 символов. Используйте отдельный пароль.</p><label htmlFor="confirm">Повторите пароль<input id="confirm" name="confirm" type="password" required minLength={12} maxLength={128} autoComplete="new-password" disabled={pending}/></label></>}
    {mode === 'verify-email' && <p className="field-hint">Нажмите кнопку, чтобы подтвердить адрес. Простое открытие ссылки не изменяет аккаунт.</p>}
    {error && <p className="form-error" role="alert">{error}</p>}
    <button className="primary" disabled={pending} type="submit">{pending ? 'Подождите…' : mode === 'forgot-password' ? 'Подготовить письмо' : mode === 'reset-password' ? 'Сохранить новый пароль' : 'Подтвердить email'} <span aria-hidden="true">↗</span></button>
    {mode !== 'forgot-password' && <a className="back-link" href={mode === 'verify-email' ? '/account' : '/forgot-password'}>Запросить новую ссылку</a>}
  </form>;
}
