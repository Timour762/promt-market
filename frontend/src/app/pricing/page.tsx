import type { Metadata } from 'next';
import SiteHeader from '../../components/SiteHeader';
import StoreFooter from '../../components/StoreFooter';
import { getCatalog } from '../../lib/catalog';
import { isCheckoutAvailable } from '../../lib/checkout';
import { isPublicPreview } from '../../lib/public-preview';
import { shopContact } from '../../lib/legal';

export const metadata: Metadata = {
  title: 'Цены и тарифы | ПромтМаркет',
  description: 'Стоимость готовых инструкций для AI, состав покупки и условия доступа. Разовая оплата за выбранный промпт, без подписки.',
};

export default async function PricingPage() {
  const catalog = await getCatalog();
  const checkout = !isPublicPreview() && isCheckoutAvailable();
  return <><SiteHeader /><main className="pricing-page">
    <a className="back-link" href="/catalog/collection">← Коллекция промптов</a>
    <p className="eyebrow">ПОНЯТНАЯ СТОИМОСТЬ</p>
    <h1>Цены и тарифы</h1>
    <p className="pricing-lead">Один промпт — одна покупка. Вы платите за готовую текстовую инструкцию для самостоятельной работы с AI.</p>
    <div className="pricing-facts"><span>Разовая оплата в рублях</span><span>Без подписки и автосписаний</span><span>Регистрация бесплатна</span></div>
    <p className="pricing-status">{checkout ? 'Оплата доступна в карточке выбранного товара. Итоговая сумма показывается до платежа.' : 'Сейчас доступны каталог и цены. Реальная оплата пока отключена; деньги не списываются.'}</p>
    <div className="pricing-table-wrap"><table className="pricing-table"><caption>Стоимость и назначение опубликованных товаров</caption><thead><tr><th scope="col">Готовая инструкция</th><th scope="col">Для какой задачи</th><th scope="col">Цена за товар</th></tr></thead><tbody>
      {catalog.map(prompt => <tr key={prompt.id}><th scope="row"><a href={`/prompts/${prompt.id}`}>{prompt.title}<span aria-hidden="true"> ↗</span></a><small>{prompt.category}</small></th><td>{prompt.description}<span>{prompt.result}</span></td><td>{prompt.price_minor === null ? 'Не назначена' : <><strong>{new Intl.NumberFormat('ru-RU', { style: 'currency', currency: prompt.currency, maximumFractionDigits: prompt.price_minor % 100 ? 2 : 0 }).format(prompt.price_minor / 100)}</strong><small>однократно</small></>}</td></tr>)}
    </tbody></table></div>
    <div className="pricing-details">
      <section><h2>Что входит в покупку</h2><p>Доступ к полному тексту одной выбранной инструкции в личной библиотеке: чтение, копирование и скачивание TXT. Поля внутри инструкции вы заполняете своими данными.</p><p>Названия и примеры описывают задачи инструкции. Товаром является текст промпта; результат работы AI зависит от выбранной модели и ваших исходных данных.</p></section>
      <section><h2>Что оплачивается отдельно</h2><p>Подписки и запросы сторонних AI-сервисов не включены. Генерация изображений или видео, консультация специалиста и индивидуальная разработка не входят в стоимость инструкции.</p><p>После подключения оплаты доступ открывается после подтверждения платежа. До оплаты будут показаны выбранный товар и итоговая сумма заказа.</p></section>
    </div>
    <aside className="pricing-support"><h2>Поможем выбрать инструкцию</h2><p>Вопросы о составе товара и доступе: <a className="card-link" href={`mailto:${shopContact.email}`}>{shopContact.email}</a>.</p><p><a className="card-link" href="/legal/terms">Пользовательское соглашение</a> · <a className="card-link" href="/legal/refunds">Обращения и возвраты</a></p></aside>
  </main><StoreFooter /></>;
}
