import type { Metadata } from 'next';
import SiteHeader from '../../../components/SiteHeader';
import StoreFooter from '../../../components/StoreFooter';
import PromptCatalog from '../../../components/PromptCatalog';
import { getCatalog } from '../../../lib/catalog';
import { isPublicPreview } from '../../../lib/public-preview';
import { isCheckoutAvailable } from '../../../lib/checkout';

export const metadata: Metadata = {
  title: 'Коллекция промптов | ПромтМаркет',
  description: 'Выберите промпт для программирования, бизнеса, маркетинга, изображений и видео.',
};

export default async function CollectionPage() {
  const catalog = await getCatalog();

  return (
    <>
      <a className="skip" href="#catalog">Перейти к каталогу</a>
      <SiteHeader />
      <main className="pv-main collection-page">
        <PromptCatalog catalog={catalog} />
        <section className="pv-how" id="how">
          <div>
            <p className="pv-kicker">ОТ ИДЕИ К ДЕЙСТВИЮ</p>
            <h2>Хороший ответ<br />начинается с вас.</h2>
          </div>
          <ol>
            {[
              ['Найдите свой промпт', 'Выберите задачу и изучите ожидаемый результат.'],
              ['Добавьте контекст', 'Замените поля в инструкции своими данными.'],
              ['Переходите к работе', 'Используйте ответ как основу и проверяйте факты.'],
            ].map(([title, text], i) => (
              <li key={title}><span>0{i + 1}</span><div><h3>{title}</h3><p>{text}</p></div></li>
            ))}
          </ol>
        </section>
        <aside className="launch-note">{isPublicPreview() ? 'Публичная витрина. Изучайте описания и примеры — регистрация и покупки откроются позже.' : !isCheckoutAvailable() ? 'Создайте аккаунт, чтобы пользоваться личным кабинетом. Покупки откроются после подключения оплаты.' : 'Оплата в рублях через Platega. Доступ к промпту открывается автоматически после подтверждения платежа.'}</aside>
      </main>
      <StoreFooter />
    </>
  );
}
