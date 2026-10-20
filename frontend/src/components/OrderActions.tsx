"use client";
import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { adminMutation } from '../lib/admin-client';
async function createOrder(promptId: string) {
  const csrf = await fetch('/api/auth/csrf', { cache: 'no-store', signal: AbortSignal.timeout(10000) });
  if (!csrf.ok) throw new Error('Не удалось подготовить запрос. Повторите попытку.');
  const { token } = await csrf.json();
  return fetch('/api/orders', { method: 'POST', headers: { 'Content-Type': 'application/json', 'X-CSRF-Token': token }, body: JSON.stringify({ prompt_id: promptId }), signal: AbortSignal.timeout(15000) });
}
export function OrderButton({ promptId }: { promptId: string }) {
  const router = useRouter(); const [busy,setBusy] = useState(false); const [error,setError] = useState('');
  async function submit() {
    setBusy(true);setError('');
    try {
      const response=await createOrder(promptId);
      if(response.status===401){ router.push('/login');return; }
      const data=await response.json();
      if(!response.ok) throw new Error(typeof data.detail==='string'?data.detail:'Не удалось создать заказ');
      router.push(`/account/orders/${data.id}`);router.refresh();
    } catch(error) { setError(error instanceof Error?error.message:'Не удалось создать заказ'); }
    finally { setBusy(false); }
  }
  return <div className="order-action"><button type="button" className="primary" disabled={busy} onClick={submit}>{busy?'Создаём заказ…':'Оформить заказ'}</button><p className="field-hint">После оформления можно оплатить в рублях через Platega. Доступ откроется автоматически после подтверждения оплаты.</p>{error&&<p className="form-error" role="alert">{error}</p>}</div>;
}
export function GrantTestAccess({ orderId }: { orderId: string }) {
  const router=useRouter();const [busy,setBusy]=useState(false);const [error,setError]=useState('');
  async function grant(){setBusy(true);setError('');try{await adminMutation(`orders/${orderId}/test-access`,'POST',{});router.refresh();}catch(error){setError(error instanceof Error?error.message:'Не удалось выдать доступ');}finally{setBusy(false);}}
  return <div><button type="button" className="secondary-button" disabled={busy} onClick={grant}>{busy?'Выдаём…':'Выдать учебный доступ'}</button>{error&&<p className="form-error" role="alert">{error}</p>}</div>;
}
export function PromptText({ content, orderId }: { content: string; orderId: string }) {
  const [message,setMessage]=useState('');
  async function copy(){try{await navigator.clipboard.writeText(content);setMessage('Текст скопирован');}catch{setMessage('Не удалось скопировать автоматически. Выделите текст ниже или скачайте TXT.');}}
  return <><div className="library-actions"><button className="primary" type="button" onClick={copy}>Скопировать текст</button><a className="secondary-button" href={`/api/library/${orderId}/download`}>Скачать TXT ↓</a></div><p role="status" aria-live="polite">{message}</p><pre className="prompt-full-text" tabIndex={0} aria-label="Полный текст промпта">{content}</pre></>;
}
