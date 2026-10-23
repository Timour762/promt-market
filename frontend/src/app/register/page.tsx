import type { Metadata } from 'next';
import { redirect } from 'next/navigation';
import SiteHeader from '../../components/SiteHeader';
import AuthForm from '../../components/AuthForm';
import { getCurrentUser } from '../../lib/auth';
export const metadata: Metadata = { title: 'Регистрация | ПромтМаркет', robots: { index: false, follow: false } };
export default async function RegisterPage() {
  if (await getCurrentUser()) redirect('/account');
  const localMode = process.env.APP_ENV !== 'production';
  return <><SiteHeader/><main className="auth-page"><a className="back-link" href="/catalog">← Вернуться в каталог</a><p className="eyebrow">НАЧНИТЕ ЗДЕСЬ</p><h1>Ваш аккаунт в ПромтМаркете</h1><p className="auth-intro">Один аккаунт для вашей коллекции промптов.</p><AuthForm mode="register" localMode={localMode}/><p className="local-auth-note">{localMode ? 'Локальная версия. Используйте учебные данные и отдельный пароль. При локальной доставке письмо сохраняется на компьютере.' : 'После регистрации проверьте письмо для подтверждения email во входящих и папке «Спам». Если оно не появится, запросите новое в личном кабинете.'}</p></main></>;
}
