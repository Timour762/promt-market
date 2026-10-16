"use client";
import { useState } from 'react';
import { authMutation } from '../lib/auth-client';
export default function VerificationNotice() {
  const [pending,setPending] = useState(false); const [sent,setSent] = useState(false); const [error,setError] = useState('');
  async function resend() {
    if (pending) return; setPending(true); setError('');
    try { await authMutation('resend-verification'); setSent(true); }
    catch (cause) { setError(cause instanceof Error ? cause.message : 'Не удалось подготовить письмо.'); }
    finally { setPending(false); }
  }
  return <div className="verification-notice"><h3>Подтвердите ваш email</h3><p>При подключённой отправке письмо придёт на ваш email. В локальном режиме оно сохраняется в папке <code>.local/mail</code> проекта. Откройте HTML-файл и перейдите по ссылке. Локальный режим не отправляет письмо наружу.</p>{sent && <p role="status">Новое письмо подготовлено. Предыдущая ссылка больше не действует.</p>}<button className="secondary-button" disabled={pending} onClick={resend}>{pending ? 'Готовим письмо…' : 'Подготовить новое письмо'}</button>{error && <p className="form-error" role="alert">{error}</p>}</div>;
}
