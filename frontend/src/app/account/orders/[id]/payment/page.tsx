import { notFound } from 'next/navigation';
import SiteHeader from '../../../../../components/SiteHeader';
import AccountNav from '../../../../../components/AccountNav';
import PlategaPayment from '../../../../../components/PlategaPayment';
import type { PlategaPaymentInfo } from '../../../../../lib/payment-types';
import { accountFetch } from '../../../../../lib/orders';
import type { Order } from '../../../../../lib/order-types';

export const metadata = { title: 'Оплата заказа | ПромтМаркет', robots: { index: false, follow: false } };

export default async function PaymentPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  if (!/^[0-9a-f-]{36}$/i.test(id)) notFound();
  const order = await accountFetch<Order>(`orders/${id}`);
  const payment = await accountFetch<PlategaPaymentInfo>(`orders/${id}/platega-payment`);
  return <><SiteHeader/><main className="account-page"><AccountNav/>
    <p className="eyebrow">ОПЛАТА · ЗАКАЗ № {id.slice(0, 8)}</p><h1>{order.title}</h1>
    <PlategaPayment order={order} initial={payment}/>
    <p><a className="card-link" href={`/account/orders/${id}`}>← Вернуться к заказу</a></p>
  </main></>;
}
