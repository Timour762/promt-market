import PaymentActions from '../../../../components/PaymentActions';
import type { PlategaPaymentInfo } from '../../../../lib/payment-types';
import { notFound } from 'next/navigation';
import SiteHeader from '../../../../components/SiteHeader';
import AccountNav from '../../../../components/AccountNav';
import { accountFetch } from '../../../../lib/orders';
import { orderPrice,orderStatus,type Order } from '../../../../lib/order-types';
export const metadata={title:'Заказ | ПромтМаркет',robots:{index:false,follow:false}};
export default async function OrderPage({params}:{params:Promise<{id:string}>}){
  const {id}=await params;if(!/^[0-9a-f-]{36}$/i.test(id))notFound();
  const order=await accountFetch<Order>(`orders/${id}`);
  const payment=await accountFetch<PlategaPaymentInfo>(`orders/${id}/platega-payment`);
  const accessible=['paid','test_granted','sandbox_paid'].includes(order.status);
  return <><SiteHeader/><main className="account-page"><AccountNav/>
    <p className="eyebrow">ЗАКАЗ № {order.id.slice(0,8)}</p><h1>{order.title}</h1>
    <section className="order-summary">
      <dl><div><dt>Стоимость при оформлении</dt><dd>{orderPrice(order)}</dd></div><div><dt>Состояние</dt><dd>{order.status==='awaiting_confirmation'?'Ожидает оплаты':orderStatus[order.status]}</dd></div></dl>
      {accessible?<>
        <h2>{order.status==='paid'?'Оплата подтверждена':order.status==='sandbox_paid'?'Тестовая оплата подтверждена':'Учебный доступ выдан'}</h2>
        <p>{order.status==='paid'?'Оплата подтверждена. Промпт доступен в вашей библиотеке.':'Промпт появился в вашей библиотеке. Это учебный доступ.'}</p>
        <a className="primary" href={`/account/library/${id}`}>Открыть полный текст ↗</a>
      </>:<PaymentActions orderId={id} enabled={payment.enabled}/>}
    </section>
    <p><a className="card-link" href="/account/orders">← Все мои заказы</a></p>
  </main></>;
}
