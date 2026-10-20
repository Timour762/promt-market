"use client";
import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { adminMutation } from '../lib/admin-client';
import { orderPrice, type Order, type PendingPayments as PendingPaymentsData } from '../lib/order-types';

export default function PendingPayments({ initial, page }: { initial: PendingPaymentsData; page: number }) {
  const router = useRouter();
  const [result, setResult] = useState(initial);
  const [busyId, setBusyId] = useState<string | null>(null);
  const [error, setError] = useState('');
  const [message, setMessage] = useState('');
  useEffect(() => { setResult(initial); }, [initial]);

  useEffect(() => {
    if (busyId) return;
    const controller = new AbortController();
    let timer: ReturnType<typeof setTimeout>;
    async function poll() {
      try {
        const response = await fetch(`/api/admin/orders/pending-payments?offset=${(page - 1) * 50}`, {
          cache: 'no-store', signal: AbortSignal.any([controller.signal, AbortSignal.timeout(10000)]),
        });
        if (!response.ok) throw new Error('Не удалось обновить список. Повторим автоматически.');
        const data: PendingPaymentsData = await response.json();
        if (!controller.signal.aborted) { setResult(data); setError(''); }
      } catch {
        if (!controller.signal.aborted) setError('Не удалось обновить список. Повторим автоматически.');
      }
      if (!controller.signal.aborted) timer = setTimeout(poll, 7000);
    }
    timer = setTimeout(poll, 7000);
    return () => { controller.abort(); clearTimeout(timer); };
  }, [page, busyId]);

  async function confirm(id: string, customer: string) {
    if (busyId) return;
    setBusyId(id); setError(''); setMessage('');
    try {
      await adminMutation<Order>(`orders/${id}/confirm-payment`, 'POST', {});
      setResult(previous => ({ total: Math.max(0, previous.total - 1), items: previous.items.filter(item => item.id !== id) }));
      setMessage(`Оплата заказа № ${id.slice(0, 8)} подтверждена. ${customer}: доступ к промпту открыт.`);
      router.refresh();
    } catch (error) { setError(error instanceof Error ? error.message : 'Не удалось подтвердить оплату.'); }
    finally { setBusyId(null); }
  }

  return <section className="pending-payments" id="pending-payments" aria-labelledby="pending-payments-title">
    <div className="pending-payments-heading"><div><p className="eyebrow">ТОЛЬКО ДЛЯ АДМИНИСТРАТОРА</p><h2 id="pending-payments-title">Ожидают подтверждения</h2></div><span className="status-badge">Заказов: {result.total}</span></div>
    <p className="pending-payments-intro">Сверьте поступление и сумму в своём банке, затем нажмите «Подтвердить» напротив покупателя. Доступ к промпту откроется сразу. Новые заказы появляются автоматически.</p>
    {message && <p className="save-message" role="status">{message}</p>}
    {error && <p className="form-error" role="alert">{error}</p>}
    <div className="pending-payments-list">{result.items.map(item => <article className="pending-payment-row" key={item.id}>
      <div className="pending-payment-customer"><strong>{item.customer_name}</strong>{item.customer_contact && <span>{item.customer_contact}</span>}<small>№ {item.id.slice(0, 8)} · {new Date(item.requested_at).toLocaleString('ru-RU', { timeZone: 'Europe/Moscow', day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' })}</small></div>
      <div className="pending-payment-product"><h3>{item.title}</h3><p>{item.recipient_name} · {item.bank_name}<br/>{item.masked_card}</p></div>
      <strong className="pending-payment-amount">{orderPrice(item)}</strong>
      <button type="button" className="primary" disabled={busyId !== null} aria-label={`Подтвердить оплату заказа ${item.id.slice(0, 8)} — ${item.customer_name}`} onClick={() => confirm(item.id, item.customer_name)}>{busyId === item.id ? 'Подтверждаем…' : 'Подтвердить'}</button>
    </article>)}</div>
    {!result.items.length && <div className="pending-payments-empty"><h3>{result.total ? 'На этой странице больше нет заказов' : 'Все оплаты проверены'}</h3><p>{result.total ? 'Вернитесь на первую страницу списка.' : 'Здесь появятся покупатели, которые перешли к оплате и ждут вашего подтверждения.'}</p>{result.total > 0 && <a className="card-link" href="/account#pending-payments">Первая страница ↗</a>}</div>}
    {(page > 1 || result.total > 50) && <nav className="pagination" aria-label="Страницы ожидающих оплат">{page > 1 && <a href={`?payments_page=${page - 1}#pending-payments`}>← Назад</a>}<span>Страница {page}</span>{page * 50 < result.total && <a href={`?payments_page=${page + 1}#pending-payments`}>Далее →</a>}</nav>}
  </section>;
}
