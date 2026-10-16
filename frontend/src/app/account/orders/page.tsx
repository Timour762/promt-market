import SiteHeader from '../../../components/SiteHeader';
import AccountNav from '../../../components/AccountNav';
import { accountFetch } from '../../../lib/orders';
import { orderPrice,orderStatus,type Order } from '../../../lib/order-types';
export const metadata={title:'Мои заказы | ПромтМаркет',robots:{index:false,follow:false}};
export default async function Orders({searchParams}:{searchParams:Promise<{page?:string}>}){
  const search=await searchParams;const page=Math.min(100000,Math.max(1,Number.parseInt(search.page??'1',10)||1));
  const items=await accountFetch<Order[]>(`orders?offset=${(page-1)*50}`);
  return <><SiteHeader/><main className="account-page"><AccountNav/><p className="eyebrow">ЛИЧНЫЙ КАБИНЕТ</p><h1>Мои заказы</h1><p className="auth-intro">Оплата пока не подключена. Деньги за эти заказы не списываются.</p><div className="order-list">{items.map(order=><article className="order-row" key={order.id}><div><span className="field-hint">{new Date(order.created_at).toLocaleDateString('ru-RU',{timeZone:'Europe/Moscow'})} · № {order.id.slice(0,8)}</span><h2><a href={`/account/orders/${order.id}`}>{order.title}</a></h2><span className="status-badge">{orderStatus[order.status]}</span></div><strong>{orderPrice(order)}</strong><a className="card-link" href={`/account/orders/${order.id}`}>Открыть заказ ↗</a></article>)}</div>{!items.length&&<section className="empty"><h2>Заказов пока нет</h2><p>Выберите промпт в каталоге и оформите заказ на его странице.</p><a className="primary" href="/catalog">Перейти в каталог</a></section>}<nav className="pagination" aria-label="Страницы заказов">{page>1&&<a href={`?page=${page-1}`}>← Назад</a>}<span>Страница {page}</span>{items.length===50&&<a href={`?page=${page+1}`}>Далее →</a>}</nav></main></>;
}
