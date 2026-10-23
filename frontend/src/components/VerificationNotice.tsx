"use client";
import { useState } from 'react';
import { authMutation } from '../lib/auth-client';
export default function VerificationNotice({ localMode = false }: { localMode?: boolean }) {
  const [pending,setPending] = useState(false); const [sent,setSent] = useState(false); const [error,setError] = useState('');
  async function resend() {
    if (pending) return; setPending(true); setError('');
    try { await authMutation('resend-verification'); setSent(true); }
    catch (cause) { setError(cause instanceof Error ? cause.message : 'Не удалось подготовить письмо.'); }
    finally { setPending(false); }
  }
  return <div className="verification-notice"><h3>Подтвердите ваш email</h3><p>Откройте ссылку из письма и подтвердите адрес. Проверьте входящие и папку «Спам». Если письмо не появится, запросите новое.{localMode && <> При локальной доставке письмо сохраняется в папке <code>.local/mail</code> проекта и наружу не отправляется.</>}</p>{sent && <p role="status">Новое письмо поставлено в очередь. Предыдущая ссылка больше не действует.</p>}<button className="secondary-button" disabled={pending} onClick={resend}>{pending ? 'Готовим письмо…' : 'Запросить новое письмо'}</button>{error && <p className="form-error" role="alert">{error}</p>}</div>;
}
