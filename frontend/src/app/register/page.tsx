import type { Metadata } from 'next';
import { redirect } from 'next/navigation';
import SiteHeader from '../../components/SiteHeader';
import AuthForm from '../../components/AuthForm';
import { getCurrentUser } from '../../lib/auth';
export const metadata: Metadata = { title: 'Регистрация | ПромтМаркет', robots: { index: false, follow: false } };
export default async function RegisterPage() {
  if (await getCurrentUser()) redirect('/account');
  return <><SiteHeader/><main className="auth-page"><a className="back-link" href="/catalog">← Вернуться в каталог</a><p className="eyebrow">НАЧНИТЕ ЗДЕСЬ</p><h1>Ваш аккаунт в ПромтМаркете</h1><p className="auth-intro">Один аккаунт для вашей будущей коллекции промптов.</p><AuthForm mode="register"/><p className="local-auth-note">Локальная версия. Для просмотра используйте учебные данные и отдельный пароль. Доставка подтверждения email зависит от настройки отправки; в локальном режиме письмо сохраняется на компьютере. Реальные покупки ещё не подключены.</p></main></>;
}
