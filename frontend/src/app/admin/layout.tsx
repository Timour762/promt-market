import type { Metadata } from 'next';
import SiteHeader from '../../components/SiteHeader';
import { requireAdmin } from '../../lib/admin';
export const metadata: Metadata = { title: 'Управление | ПромтМаркет', robots: { index: false, follow: false } };
export default async function AdminLayout({ children }: { children: React.ReactNode }) {
  await requireAdmin();
  return <><SiteHeader/><main className="admin-page"><nav className="admin-nav" aria-label="Управление магазином"><a href="/admin">Обзор</a><a href="/admin/prompts">Товары</a><a href="/admin/orders">Заказы</a><a href="/admin/payments">Платежи</a><a href="/admin/audit">Журнал изменений</a><a href="/catalog">Открыть витрину ↗</a></nav>{children}</main></>;
}
