"use client";
import { useEffect, useState, type FormEvent } from 'react';
import { useRouter } from 'next/navigation';
import { authMutation } from '../lib/auth-client';
export default function AuthForm({ mode, localMode = false }: { mode: 'login' | 'register'; localMode?: boolean }) {
  const register = mode === 'register';
  const router = useRouter();
  const [ready, setReady] = useState(false);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState('');
  useEffect(() => { setReady(true); }, []);
  const disabled = !ready || pending;
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); if (!ready || pending) return;
    const form = new FormData(event.currentTarget);
    const password = String(form.get('password') ?? '');
    if (register && password !== form.get('confirm')) { setError('Пароли не совпадают'); return; }
    setPending(true); setError('');
    try {
      await authMutation(mode, { email: String(form.get('email') ?? ''), password, ...(register ? { name: String(form.get('name') ?? '') } : {}) });
      router.replace('/account'); router.refresh();
    } catch (cause) {
      setError(cause instanceof Error && cause.name !== 'TimeoutError' ? cause.message : 'Не удалось подключиться. Попробуйте ещё раз.');
      setPending(false);
    }
  }
  return <form className="auth-form" method="post" onSubmit={submit} aria-busy={pending}>
    {register && <label htmlFor="name">Ваше имя<input id="name" name="name" autoComplete="name" required minLength={1} maxLength={80} disabled={disabled}/></label>}
    <label htmlFor="email">{register ? 'Email' : 'Логин или email'}<input id="email" name="email" type={register ? 'email' : 'text'} autoComplete={register ? 'email' : 'username'} required maxLength={254} disabled={disabled}/></label>
    <label htmlFor="password">Пароль<input id="password" name="password" type="password" autoComplete={register ? 'new-password' : 'current-password'} required minLength={register ? 12 : 1} maxLength={128} aria-describedby={register ? 'password-hint' : undefined} disabled={disabled}/></label>
    {register && <><p className="field-hint" id="password-hint">От 12 до 128 символов. Можно использовать длинную фразу.</p><label htmlFor="confirm">Повторите пароль<input id="confirm" name="confirm" type="password" autoComplete="new-password" required minLength={12} maxLength={128} disabled={disabled}/></label></>}
    {register && <p className="field-hint">Перед регистрацией ознакомьтесь с <a className="card-link" href="/legal/privacy">{localMode ? 'проектом политики конфиденциальности' : 'политикой конфиденциальности'}</a>. Создание аккаунта не оформляет покупку.{localMode && ' Сейчас это локальная версия для разработки.'}</p>}
    {error && <p className="form-error" role="alert">{error}</p>}
    <noscript><p className="field-hint">Для входа и регистрации включите JavaScript в браузере.</p></noscript>
    <button className="primary" type="submit" disabled={disabled}>{pending ? 'Подождите…' : register ? 'Создать аккаунт' : 'Войти'}<span aria-hidden="true">↗</span></button>
    {!register && <a className="forgot-link" href="/forgot-password">Не помню пароль</a>}
    <p className="auth-switch">{register ? 'Уже есть аккаунт?' : 'Впервые здесь?'} <a href={register ? '/login' : '/register'}>{register ? 'Войти' : 'Создать аккаунт'}</a></p>
  </form>;
}
