"use client";
import { useEffect, useState } from 'react';
import { orderPrice, type Order } from '../lib/order-types';
import { paymentMutation, safePlategaUrl, type PlategaPaymentInfo } from '../lib/payment-types';
import PaymentActions from './PaymentActions';

export default function PlategaPayment({ order, initial }: { order: Order; initial: PlategaPaymentInfo }) {
  const [payment, setPayment] = useState(initial);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const accessible = ['paid', 'test_granted', 'sandbox_paid'].includes(payment.status);
  const closed = ['CANCELED', 'EXPIRED', 'FAILED'].includes(payment.provider_status ?? '');
  const uncertain = ['CREATED', 'UNKNOWN'].includes(payment.provider_status ?? '');
  const chargeback = payment.provider_status === 'CHARGEBACKED';
  const checkout = safePlategaUrl(payment.checkout_url);

  useEffect(() => {
    if (accessible || closed || chargeback || !payment.provider_status || uncertain) return;
    let stopped = false;
    let timer: ReturnType<typeof setTimeout>;
    async function poll() {
      try {
        const result = await paymentMutation(order.id, 'check');
        if (!stopped) { setPayment(result); setError(''); }
      } catch (error) {
        if (!stopped) setError(error instanceof Error ? error.message : 'Статус временно недоступен. Повторим проверку автоматически.');
      }
      if (!stopped) timer = setTimeout(poll, 5000);
    }
    void poll();
    return () => { stopped = true; clearTimeout(timer); };
  }, [order.id, accessible, closed, chargeback, uncertain, payment.provider_status]);

  async function check() {
    if (busy) return;
    setBusy(true); setError('');
    try { setPayment(await paymentMutation(order.id, 'check')); }
    catch (error) { setError(error instanceof Error ? error.message : 'Не удалось проверить оплату.'); }
    finally { setBusy(false); }
  }

  return <section className="manual-payment-panel order-summary">
    <dl><div><dt>Стоимость заказа</dt><dd>{orderPrice(order)}</dd></div><div><dt>Способ оплаты</dt><dd>Platega · СБП</dd></div></dl>
    {accessible ? <div className="payment-success" role="status"><span className="payment-success-icon" aria-hidden="true">✓</span><h2>Оплата подтверждена</h2><p>Промпт доступен в вашей библиотеке.</p><a className="primary" href={`/account/library/${order.id}`}>Открыть промпт ↗</a></div>
      : chargeback ? <><h2>Платёж возвращён</h2><p>Platega сообщила о возврате платежа. Доступ к промпту закрыт. Для уточнения обратитесь в поддержку.</p></>
      : uncertain ? <><h2>Уточняем состояние платежа</h2><p>Создание платежа пока не подтверждено. Обратитесь к администратору перед повторной оплатой.</p><button type="button" className="secondary-button" disabled={busy} onClick={check}>Проверить оплату</button></>
      : closed ? <><h2>{payment.provider_status === 'EXPIRED' ? 'Время оплаты истекло' : 'Платёж не завершён'}</h2><p>Предыдущая платёжная ссылка закрыта. Можно создать новую и повторить оплату.</p><PaymentActions orderId={order.id} enabled={payment.enabled}/></>
      : !payment.provider_status ? <PaymentActions orderId={order.id} enabled={payment.enabled}/>
      : <><h2>Оплата через Platega</h2><p>Завершите оплату в рублях на странице Platega, затем вернитесь сюда. Доступ откроется автоматически после подтверждения сервисом.</p>
        {checkout && <a className="primary" href={checkout}>Продолжить оплату в Platega ↗</a>}
        <div className="payment-waiting" role="status" aria-live="polite"><span className="payment-spinner" aria-hidden="true"/><div><h3>Ожидаем подтверждение Platega</h3><p>Проверяем статус автоматически. Повторно оплачивать заказ не нужно.</p></div></div>
        <button type="button" className="secondary-button" disabled={busy} onClick={check}>{busy ? 'Проверяем…' : 'Проверить оплату'}</button>
      </>}
    {error && <p className="form-error" role="alert">{error}</p>}
  </section>;
}
