"use client";
import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { paymentMutation, safePlategaUrl } from '../lib/payment-types';

export default function PaymentActions({ orderId, enabled = true }: { orderId: string; enabled?: boolean }) {
  const router = useRouter();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');

  async function pay() {
    if (!enabled || busy) return;
    setBusy(true);
    setError('');
    try {
      const data = await paymentMutation(orderId, 'start');
      if (['paid','test_granted','sandbox_paid'].includes(data.status)) { router.push(`/account/orders/${orderId}/payment`); return; }
      const url = safePlategaUrl(data.checkout_url);
      if (!url) throw new Error('Не удалось получить платёжную ссылку Platega. Обратитесь к администратору.');
      window.location.assign(url);
    } catch (error) {
      setError(error instanceof Error ? error.message : 'Сервис временно недоступен. Попробуйте ещё раз.');
      setBusy(false);
    }
  }

  return <div className="payment-actions" aria-busy={busy}>
    <h2>Оплата через Platega</h2>
    <p id={`payment-help-${orderId}`}>{enabled ? 'Оплатите заказ в рублях через СБП на платёжной странице Platega. После подтверждения платежа промпт автоматически появится в библиотеке.' : 'Магазин ещё не подключён к Platega, поэтому оплата пока недоступна. Ваш заказ сохранён.'}</p>
    <button type="button" className="primary" disabled={!enabled || busy} aria-describedby={`payment-help-${orderId}`} onClick={pay}>{busy ? 'Открываем Platega…' : enabled ? 'Оплатить' : 'Platega не подключена'}</button>
    {error && <p className="form-error" role="alert">{error}</p>}
  </div>;
}
