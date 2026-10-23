import type { Metadata } from 'next';
import SiteHeader from '../../components/SiteHeader';
import RecoveryForm from '../../components/RecoveryForm';
export const metadata: Metadata = { title: 'Восстановление пароля | ПромтМаркет', robots: { index: false, follow: false }, referrer: 'no-referrer' };
export default function RecoveryPage() {
 const localMode = process.env.APP_ENV !== 'production';
 return <><SiteHeader/><main className="auth-page"><a className="back-link" href="/login">← Ко входу</a><p className="eyebrow">ДОСТУП К АККАУНТУ</p><h1>Восстановление пароля</h1><p className="auth-intro">Введите email аккаунта. Подготовим одноразовую ссылку на смену пароля.</p><RecoveryForm mode="forgot-password" localMode={localMode}/><p className="local-auth-note">{localMode ? 'При локальной доставке письма сохраняются на компьютере.' : 'Письмо может прийти не сразу. Проверьте входящие и папку «Спам».'}</p></main></>;
}
