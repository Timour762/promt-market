import type { Metadata } from 'next';
import SiteHeader from '../../components/SiteHeader';
import RecoveryForm from '../../components/RecoveryForm';
export const metadata: Metadata = { title: 'Подтверждение email | ПромтМаркет', robots: { index: false, follow: false }, referrer: 'no-referrer' };
export default function RecoveryPage() {
 const localMode = process.env.APP_ENV !== 'production';
 return <><SiteHeader/><main className="auth-page"><a className="back-link" href="/login">← Ко входу</a><p className="eyebrow">ДОСТУП К АККАУНТУ</p><h1>Подтверждение email</h1><p className="auth-intro">Подтвердите, что адрес принадлежит вам.</p><RecoveryForm mode="verify-email" localMode={localMode}/><p className="local-auth-note">{localMode ? 'При локальной доставке письмо сохраняется на компьютере.' : 'Ссылка из письма действует один час. Новое письмо отменяет предыдущую ссылку.'}</p></main></>;
}
