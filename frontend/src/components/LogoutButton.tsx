"use client";
import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { authMutation } from '../lib/auth-client';
export default function LogoutButton() {
  const router = useRouter(); const [pending,setPending] = useState(false); const [error,setError] = useState('');
  async function logout() {
    if (pending) return; setPending(true); setError('');
    try { await authMutation('logout'); router.replace('/login'); router.refresh(); }
    catch { setError('Не удалось выйти. Повторите попытку.'); setPending(false); }
  }
  return <div><button className="secondary-button" disabled={pending} onClick={logout}>{pending ? 'Выходим…' : 'Выйти из аккаунта'}</button>{error && <p className="form-error" role="alert">{error}</p>}</div>;
}
