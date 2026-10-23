import type { Metadata } from 'next';
import SiteHeader from '../../components/SiteHeader';
import RecoveryForm from '../../components/RecoveryForm';
export const metadata: Metadata = { title: 'Новый пароль | ПромтМаркет', robots: { index: false, follow: false }, referrer: 'no-referrer' };
export default function RecoveryPage() {
 const localMode = process.env.APP_ENV !== 'production';
 return <><SiteHeader/><main className="auth-page"><a className="back-link" href="/login">← Ко входу</a><p className="eyebrow">ДОСТУП К АККАУНТУ</p><h1>Новый пароль</h1><p className="auth-intro">После смены пароля все прежние сеансы будут завершены.</p><RecoveryForm mode="reset-password" localMode={localMode}/><p className="local-auth-note">{localMode ? 'При локальной доставке письмо сохраняется на компьютере.' : 'Ссылка для смены пароля действует 30 минут и используется один раз.'}</p></main></>;
}
