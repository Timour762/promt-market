"use client";
import { useEffect, useState } from 'react';
import PaymentActions from './PaymentActions';
import { orderPrice, orderStatus, type Order, type PaymentDetails } from '../lib/order-types';

export default function ManualPayment({ order, initial }: { order: Order; initial: PaymentDetails }) {
  const [status, setStatus] = useState(initial.status);
  const [error, setError] = useState('');
  const [copyMessage, setCopyMessage] = useState('');
  const recipient = initial.recipient;
  const accessible = ['paid', 'test_granted', 'sandbox_paid'].includes(status);

  useEffect(() => {
    if (status !== 'awaiting_confirmation') return;
    const controller = new AbortController();
    let timer: ReturnType<typeof setTimeout>;
    async function poll() {
      try {
        const response = await fetch(`/api/payments/${order.id}/status`, {
          cache: 'no-store', signal: AbortSignal.any([controller.signal, AbortSignal.timeout(10000)]),
        });
        if (response.status === 401) {
          setError('Сессия завершилась. Войдите в аккаунт, чтобы проверить подтверждение.');
          return;
        }
        if (!response.ok) throw new Error('Статус временно недоступен. Продолжаем проверку автоматически.');
        const data: Pick<PaymentDetails, 'status'> = await response.json();
        if (controller.signal.aborted) return;
        setStatus(data.status);
        setError('');
      } catch (error) {
        if (controller.signal.aborted) return;
        setError(error instanceof Error && error.name !== 'TimeoutError' ? error.message : 'Проверка заняла больше времени. Повторяем автоматически.');
      }
      if (!controller.signal.aborted) timer = setTimeout(poll, 5000);
    }
    void poll();
    return () => { controller.abort(); clearTimeout(timer); };
  }, [order.id, status]);

  async function copyCard() {
    if (!recipient) return;
    try { await navigator.clipboard.writeText(recipient.card_number); setCopyMessage('Номер карты скопирован'); }
    catch { setCopyMessage('Выделите и скопируйте номер карты вручную.'); }
  }

  return <section className="manual-payment-panel order-summary">
    <dl><div><dt>Сумма к оплате</dt><dd>{orderPrice(order)}</dd></div><div><dt>Состояние</dt><dd>{orderStatus[status]}</dd></div></dl>
    {accessible ? <div className="payment-success" role="status">
      <span className="payment-success-icon" aria-hidden="true">✓</span>
      <h2>{status === 'paid' ? 'Оплата подтверждена' : 'Доступ открыт'}</h2>
      <p>Промпт уже в вашей библиотеке. Можно открыть полный текст и скачать его.</p>
      <a className="primary" href={`/account/library/${order.id}`}>Открыть промпт ↗</a>
    </div> : status === 'awaiting_confirmation' ? <>
      <h2>Реквизиты получателя</h2>
      {recipient && <div className="transfer-recipient">
        <dl><div><dt>Получатель</dt><dd>{recipient.recipient_name}</dd></div><div><dt>Банк получателя</dt><dd>{recipient.bank_name}</dd></div></dl>
        <div className="transfer-card"><span>Номер карты</span><div><strong>{recipient.card_number.replace(/(.{4})(?=.)/g, '$1 ')}</strong><button type="button" className="secondary-button" onClick={copyCard}>Скопировать</button></div></div>
        {copyMessage && <p role="status">{copyMessage}</p>}
      </div>}
      <p>Переведите <strong>{orderPrice(order)}</strong> по указанным реквизитам. Перед переводом сверьте имя получателя в приложении банка.</p>
      <div className="payment-waiting" role="status" aria-live="polite">
        <span className="payment-spinner" aria-hidden="true"/>
        <div><h3>Ожидаем подтверждение администратора</h3><p>После перевода дождитесь проверки. Страница обновит статус автоматически и покажет доступ к промпту.</p></div>
      </div>
      <p className="field-hint">Если вы уже перевели деньги, повторно переводить их не нужно.</p>
      {error && <p className="form-error" role="alert">{error} <a href="/login">Войти</a></p>}
    </> : <PaymentActions orderId={order.id}/>}
  </section>;
}
