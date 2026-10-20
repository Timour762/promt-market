import PromptCover from '../../../components/PromptCover';
import SiteHeader from '../../../components/SiteHeader';
import AccountNav from '../../../components/AccountNav';
import { accountFetch } from '../../../lib/orders';
import type { Order } from '../../../lib/order-types';
export const metadata={title:'Моя библиотека | ПромтМаркет',robots:{index:false,follow:false}};
export default async function Library({searchParams}:{searchParams:Promise<{page?:string}>}){
  const search=await searchParams;const page=Math.min(100000,Math.max(1,Number.parseInt(search.page??'1',10)||1));
  const items=await accountFetch<Order[]>(`library?offset=${(page-1)*50}`);
  return <><SiteHeader/><main className="account-page"><AccountNav/><p className="eyebrow">ВАША КОЛЛЕКЦИЯ</p><h1>Моя библиотека</h1><p className="auth-intro">Открывайте доступные промпты, копируйте инструкции или скачивайте их в TXT.</p><div className="library-grid">{items.map(order=><article className="library-item" key={order.id}><a href={`/account/library/${order.id}`} aria-label={`Открыть ${order.title}`}><PromptCover id={order.prompt_id} category="Моя библиотека" label="ВАША ИНСТРУКЦИЯ"/></a><span className="status-badge">{order.status==='paid'?'Оплачен':order.status==='sandbox_paid'?'Тестовая оплата':'Учебный доступ'}</span><h2>{order.title}</h2><p>Сохранённая версия промпта из вашего заказа.</p><a className="card-link" href={`/account/library/${order.id}`}>Открыть текст ↗</a></article>)}</div>{!items.length&&<section className="empty"><h2>Библиотека пока пуста</h2><p>Промпты появятся здесь после подтверждения оплаты.</p><a className="primary" href="/catalog">Выбрать промпт</a></section>}<nav className="pagination" aria-label="Страницы библиотеки">{page>1&&<a href={`?page=${page-1}`}>← Назад</a>}<span>Страница {page}</span>{items.length===50&&<a href={`?page=${page+1}`}>Далее →</a>}</nav></main></>;
}
