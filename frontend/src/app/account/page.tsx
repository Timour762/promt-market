import PlategaSetup from '../../components/PlategaSetup';
import type { PlategaSetup as PlategaSetupData } from '../../lib/payment-types';
import PendingPayments from '../../components/PendingPayments';
import type { PendingPayments as PendingPaymentsData } from '../../lib/order-types';
import { adminFetch } from '../../lib/admin';
import type { Metadata } from 'next';
import { redirect } from 'next/navigation';
import SiteHeader from '../../components/SiteHeader';
import AccountNav from '../../components/AccountNav';
import AccountHero from '../../components/AccountHero';
import AccountOrbit from '../../components/AccountOrbit';
import LogoutButton from '../../components/LogoutButton';
import VerificationNotice from '../../components/VerificationNotice';
import { getCurrentUser } from '../../lib/auth';
export const metadata: Metadata = { title: 'Личный кабинет | ПромтМаркет', robots: { index: false, follow: false } };
export default async function AccountPage({searchParams}:{searchParams:Promise<{payments_page?:string}>}) {
  const user = await getCurrentUser();
  if (!user) redirect('/login');
  const setup = user.role === 'admin' ? await adminFetch<PlategaSetupData>('payments/setup') : null;
  const search = await searchParams;
  const paymentsPage = Math.min(100000, Math.max(1, Number.parseInt(search.payments_page ?? '1', 10) || 1));
  const pending = user.role === 'admin' ? await adminFetch<PendingPaymentsData>(`orders/pending-payments?offset=${(paymentsPage-1)*50}`) : null;
  return <div className="neural-storefront account-storefront"><SiteHeader/><main className="neural-main"><AccountHero name={user.name}/><section className="account-workspace" id="account-details" aria-label="Профиль и настройки"><div className="account-page account-content"><AccountNav/>
    <div className="account-layout">
      <section className="profile-section" aria-labelledby="profile-title"><h2 id="profile-title">Ваш профиль</h2>
        <dl><div><dt>Имя</dt><dd>{user.name}</dd></div><div><dt>Email</dt><dd>{user.email ?? 'Не указан'}</dd></div><div><dt>Подтверждение email</dt><dd>{!user.email ? 'Email не указан' : user.email_verified ? 'Подтверждён' : 'Пока не подтверждён'}</dd></div></dl>
        {user.email && !user.email_verified && <VerificationNotice localMode={process.env.APP_ENV !== 'production'}/>}
        {user.role === 'admin' && <><p><a className="card-link" href="#platega-settings">Оплата через Platega ↓</a></p><p><a className="card-link" href="/admin">Управление магазином ↗</a></p></>}
        <LogoutButton/>
      </section>
      <section className="library-section" aria-labelledby="library-title"><div className="account-library-heading"><div><p className="eyebrow">ВАША КОЛЛЕКЦИЯ</p><h2 id="library-title">Промпты всегда под рукой</h2></div><AccountOrbit/></div>
        <p>Открывайте доступные инструкции, копируйте текст и скачивайте TXT. После подтверждения оплаты промпт появится здесь.</p>
        <a className="primary" href="/account/library">Моя библиотека <span>↗</span></a><p><a className="card-link" href="/account/orders">Посмотреть мои заказы ↗</a></p>
      </section>
    </div>
    {setup && <PlategaSetup setup={setup}/>}
    {pending && pending.total > 0 && <PendingPayments initial={pending} page={paymentsPage}/>}
  </div></section></main></div>;
}
