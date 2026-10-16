import PaymentActions from '../../../../components/PaymentActions';
import { notFound } from 'next/navigation';
import SiteHeader from '../../../../components/SiteHeader';
import AccountNav from '../../../../components/AccountNav';
import { accountFetch } from '../../../../lib/orders';
import { orderPrice,orderStatus,type Order } from '../../../../lib/order-types';
export const metadata={title:'Заказ | ПромтМаркет',robots:{index:false,follow:false}};
export default async function OrderPage({params}:{params:Promise<{id:string}>}){
  const {id}=await params;if(!/^[0-9a-f-]{36}$/i.test(id))notFound();
  const order=await accountFetch<Order>(`orders/${id}`);
  const payment=await accountFetch<{enabled:boolean}>(`orders/${id}/payment`);
  return <><SiteHeader/><main className="account-page"><AccountNav/><p className="eyebrow">ЗАКАЗ № {order.id.slice(0,8)}</p><h1>{order.title}</h1><section className="order-summary"><dl><div><dt>Стоимость при оформлении</dt><dd>{orderPrice(order)}</dd></div><div><dt>Состояние</dt><dd>{orderStatus[order.status]}</dd></div></dl>{order.status!=='pending'?<><h2>{order.status==='sandbox_paid'?'Тестовая оплата подтверждена':'Учебный доступ выдан'}</h2><p>Промпт появился в вашей библиотеке. Это локальный учебный доступ, оплата не получена.</p><a className="primary" href={`/account/library/${id}`}>Открыть полный текст ↗</a></>:<><PaymentActions orderId={id} enabled={payment.enabled}/></>}</section><p><a className="card-link" href="/account/orders">← Все мои заказы</a></p></main></>;
}
