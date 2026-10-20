import { adminFetch } from '../../../lib/admin';
import type { PlategaSetup } from '../../../lib/payment-types';
export const metadata = { title: 'Платежи | ПромтМаркет', robots: { index: false, follow: false } };
type Transaction = { id: string; order_id: string; title: string; customer: string; price_minor: number; currency: string; status: string; amount_usdt: string | null; created_at: string };
const labels: Record<string, string> = { CREATED: 'Создаётся', UNKNOWN: 'Требует проверки', PENDING: 'Ожидает оплаты', CONFIRMED: 'Подтверждён', CANCELED: 'Отменён', EXPIRED: 'Время истекло', FAILED: 'Ошибка создания', CHARGEBACKED: 'Возвращён' };

export default async function PaymentsPage({ searchParams }: { searchParams: Promise<{ page?: string }> }) {
  const search = await searchParams;
  const page = Math.min(100000, Math.max(1, Number.parseInt(search.page ?? '1', 10) || 1));
  const setup = await adminFetch<PlategaSetup>('payments/setup');
  const history = await adminFetch<{ items: Transaction[] }>(`payments/platega?offset=${(page - 1) * 50}`);
  return <><p className="eyebrow">УПРАВЛЕНИЕ МАГАЗИНОМ</p><h1>Платежи · Platega</h1><p className="admin-intro">Приём рублей через СБП, автоматическое открытие доступа и выплаты в USDT через кабинет Platega.</p>
    <section className="payment-setup-status" aria-labelledby="payment-state"><div><span className={`status-badge${setup.live_enabled ? ' published' : ''}`}>{setup.live_enabled ? 'Приём оплаты включён' : 'Ожидает подключения'}</span><h2 id="payment-state">{setup.live_enabled ? 'Platega настроена' : 'Подключите магазин в Platega'}</h2><p>{setup.live_enabled ? 'Платёжные ссылки создаются для заказов. Доступ открывается после проверки суммы и подтверждения сервиса.' : 'Получите доступ к кабинету Platega, согласуйте приём RUB и вывод USDT, затем добавьте данные магазина на сервер.'}</p></div><a className="secondary-button" href="/admin/payments">Обновить состояние</a></section>
    <div className="payment-setup-grid">
      <section className="payment-setup-section"><h2>Состояние подключения</h2><dl className="payment-setup-list">
        <div><dt>Провайдер</dt><dd>Platega</dd></div><div><dt>Оплата покупателя</dt><dd>Рубли · СБП</dd></div>
        <div><dt>Merchant ID</dt><dd>{setup.merchant_id_configured ? 'Задан' : 'Не задан'}</dd></div><div><dt>API Secret</dt><dd>{setup.secret_configured ? 'Задан' : 'Не задан'}</dd></div>
        <div><dt>Публичный HTTPS-адрес</dt><dd>{setup.public_url_configured ? 'Задан' : 'Требуется для уведомлений'}</dd></div>
        <div><dt>Приём платежей</dt><dd>{setup.live_enabled ? 'Включён' : 'Выключен'}</dd></div><div><dt>Подтверждение оплаты</dt><dd>Автоматически через Platega</dd></div>
        <div><dt>URL уведомлений</dt><dd><code>{setup.webhook_url ?? setup.webhook_path}</code>{!setup.webhook_url && <p className="field-hint">Полный адрес появится после настройки публичного домена.</p>}</dd></div>
        <div><dt>Кошелёк и сеть USDT</dt><dd>Настраиваются в кабинете Platega</dd></div><div><dt>Связь с сервисом</dt><dd>Проверяется при первом платеже</dd></div>
      </dl></section>
      <section className="payment-setup-section"><h2>Как подключить</h2><ol className="payment-setup-steps">
        <li><strong>Подключить магазин</strong><p>Оставьте заявку в Platega и получите кабинет после согласования условий.</p></li>
        <li><strong>Настроить выплаты USDT</strong><p>Согласуйте конвертацию RUB в USDT, комиссии, сеть, адрес кошелька и порядок выплат с Platega.</p></li>
        <li><strong>Добавить данные магазина</strong><p>Merchant ID и API Secret сохраняются в закрытой конфигурации сервера. После настройки включается приём платежей.</p></li>
        <li><strong>Настроить уведомления и проверить заказ</strong><p>В кабинете Platega укажите публичный HTTPS-адрес уведомлений из списка слева. После оплаты проверьте автоматическое появление промпта в библиотеке.</p></li>
      </ol><div className="library-actions"><a className="primary" href="https://platega.io/ru" target="_blank" rel="noopener noreferrer">Подключить Platega ↗</a><a className="card-link" href="https://my.platega.io" target="_blank" rel="noopener noreferrer">Кабинет Platega ↗</a></div></section>
    </div>
    <section className="payment-history"><h2>История платежей</h2>{history.items.length ? <div className="admin-table-wrap"><table className="admin-table"><thead><tr><th>Заказ / покупатель</th><th>Сумма</th><th>Статус Platega</th><th>USDT по данным сервиса</th></tr></thead><tbody>{history.items.map(item => <tr key={item.id}><td><strong className="table-title">{item.title}</strong><span className="table-slug">{item.customer} · № {item.order_id.slice(0, 8)}</span></td><td>{new Intl.NumberFormat('ru-RU', { style: 'currency', currency: item.currency }).format(item.price_minor / 100)}</td><td><span className="status-badge">{labels[item.status] ?? item.status}</span></td><td>{item.amount_usdt === null ? '—' : `${Number(item.amount_usdt).toLocaleString('ru-RU', { maximumFractionDigits: 8 })} USDT`}</td></tr>)}</tbody></table></div> : <p className="admin-intro">Здесь появятся платежи покупателей после подключения магазина. Данные о выплатах на кошелёк доступны в кабинете Platega.</p>}</section>
    <nav className="pagination" aria-label="Страницы платежей">{page > 1 && <a href={`?page=${page - 1}`}>← Назад</a>}<span>Страница {page}</span>{history.items.length === 50 && <a href={`?page=${page + 1}`}>Далее →</a>}</nav>
  </>;
}
