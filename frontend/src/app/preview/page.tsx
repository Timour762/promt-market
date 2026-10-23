import { redirect } from 'next/navigation';
import SiteHeader from '../../components/SiteHeader';
import StoreFooter from '../../components/StoreFooter';
import { isPublicPreview } from '../../lib/public-preview';
import { isCheckoutAvailable } from '../../lib/checkout';

export const metadata = { title: 'Скоро открытие | ПромтМаркет', robots: { index: false, follow: false } };

export default function PreviewPage() {
  if (!isPublicPreview() && isCheckoutAvailable()) redirect('/catalog/collection');
  if (!isPublicPreview()) return <><SiteHeader/><main className="legal-page"><p className="eyebrow">ЛИЧНЫЙ КАБИНЕТ ОТКРЫТ</p><h1>Готовим покупки к запуску</h1><p>Регистрация и личный кабинет уже доступны. Изучайте коллекцию и примеры; оплату подключим к открытию продаж.</p><a className="primary" href="/register">Создать аккаунт ↗</a></main><StoreFooter/></>;
  return <><SiteHeader/><main className="legal-page"><p className="eyebrow">ПУБЛИЧНАЯ ВИТРИНА</p><h1>Готовимся к запуску</h1><p>Познакомьтесь с коллекцией промптов, изучите описания и примеры применения.</p><p>Регистрация, личный кабинет и покупки откроются позже. Сейчас сайт работает как витрина.</p><a className="primary" href="/catalog/collection">Посмотреть коллекцию ↗</a></main><StoreFooter/></>;
}
