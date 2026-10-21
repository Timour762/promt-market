import { redirect } from 'next/navigation';
import SiteHeader from '../../components/SiteHeader';
import StoreFooter from '../../components/StoreFooter';
import { isPublicPreview } from '../../lib/public-preview';

export const metadata = { title: 'Скоро открытие | ПромтМаркет', robots: { index: false, follow: false } };

export default function PreviewPage() {
  if (!isPublicPreview()) redirect('/catalog/collection');
  return <><SiteHeader/><main className="legal-page"><p className="eyebrow">ПУБЛИЧНАЯ ВИТРИНА</p><h1>Готовимся к запуску</h1><p>Познакомьтесь с коллекцией промптов, изучите описания и примеры применения.</p><p>Регистрация, личный кабинет и покупки откроются позже. Сейчас сайт работает как витрина.</p><a className="primary" href="/catalog/collection">Посмотреть коллекцию ↗</a></main><StoreFooter/></>;
}
