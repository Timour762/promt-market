import type { Metadata } from 'next';
import { redirect } from 'next/navigation';
import SiteHeader from '../../components/SiteHeader';
import AccountNav from '../../components/AccountNav';
import LogoutButton from '../../components/LogoutButton';
import VerificationNotice from '../../components/VerificationNotice';
import { getCurrentUser } from '../../lib/auth';
export const metadata: Metadata = { title: 'Личный кабинет | ПромтМаркет', robots: { index: false, follow: false } };
export default async function AccountPage() {
  const user = await getCurrentUser();
  if (!user) redirect('/login');
  return <><SiteHeader/><main className="account-page"><AccountNav/><p className="eyebrow">ЛИЧНЫЙ КАБИНЕТ</p><h1>Здравствуйте, {user.name}</h1><p className="auth-intro">Ваш профиль, библиотека промптов и история заказов.</p><div className="account-layout"><section className="profile-section" aria-labelledby="profile-title"><h2 id="profile-title">Ваш профиль</h2><dl><div><dt>Имя</dt><dd>{user.name}</dd></div><div><dt>Email</dt><dd>{user.email ?? 'Не указан'}</dd></div><div><dt>Подтверждение email</dt><dd>{!user.email ? 'Email не указан' : user.email_verified ? 'Подтверждён' : 'Пока не подтверждён'}</dd></div></dl>{user.email && !user.email_verified && <VerificationNotice/>}{user.role === 'admin' && <p><a className="card-link" href="/admin">Управление магазином ↗</a></p>}<LogoutButton/></section><section className="library-section" aria-labelledby="library-title"><p className="eyebrow">ВАША КОЛЛЕКЦИЯ</p><h2 id="library-title">Промпты всегда под рукой</h2><p>Открывайте доступные инструкции, копируйте текст и скачивайте TXT. Оплата пока не подключена; учебный доступ выдаёт администратор.</p><a className="primary" href="/account/library">Моя библиотека <span>↗</span></a><p><a className="card-link" href="/account/orders">Посмотреть мои заказы ↗</a></p></section></div></main></>;
}
