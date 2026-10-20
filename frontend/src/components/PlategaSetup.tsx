import type { PlategaSetup as Setup } from '../lib/payment-types';

export default function PlategaSetup({ setup }: { setup: Setup }) {
  return <section className="recipient-settings platega-settings" id="platega-settings" aria-labelledby="platega-title">
    <div className="recipient-heading"><div><p className="eyebrow">ОПЛАТА МАГАЗИНА</p><h2 id="platega-title">Platega · рубли и USDT</h2><p>Покупатели оплачивают заказы в рублях. Конвертация и выплаты USDT на ваш кошелёк настраиваются с Platega.</p></div><span className={`status-badge${setup.live_enabled ? ' published' : ''}`}>{setup.live_enabled ? 'Приём оплаты включён' : 'Ожидает подключения'}</span></div>
    <p className="field-hint">{setup.live_enabled ? 'Доступ к промптам открывается автоматически после проверки платежа. История операций доступна в разделе «Платежи».' : 'Подключите магазин в Platega, получите Merchant ID и API Secret, затем добавьте их в настройки сервера. Адрес и сеть кошелька USDT укажите в кабинете Platega.'}</p>
    <div className="library-actions"><a className="primary" href="/admin/payments">Настройка оплаты ↗</a><a className="card-link" href="https://platega.io/ru" target="_blank" rel="noopener noreferrer">Подключить магазин в Platega ↗</a></div>
  </section>;
}
