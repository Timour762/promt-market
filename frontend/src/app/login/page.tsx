import type { Metadata } from 'next';
import { redirect } from 'next/navigation';
import SiteHeader from '../../components/SiteHeader';
import AuthForm from '../../components/AuthForm';
import { getCurrentUser } from '../../lib/auth';
export const metadata: Metadata = { title: 'Вход | ПромтМаркет', robots: { index: false, follow: false } };
export default async function LoginPage() {
  if (await getCurrentUser()) redirect('/account');
  return <><SiteHeader/><main className="auth-page"><a className="back-link" href="/catalog">← Вернуться в каталог</a><p className="eyebrow">ВАШ АККАУНТ</p><h1>Рады видеть вас снова</h1><p className="auth-intro">Войдите, чтобы открыть личный кабинет.</p><AuthForm mode="login"/><p className="local-auth-note">Пока это локальная версия. Письма для восстановления сохраняются на компьютере, без отправки на email.</p></main></>;
}
