import { adminFetch } from '../../lib/admin';
export default async function AdminPage() {
  const stats = await adminFetch<{ prompts: number; published: number; draft: number; archived: number }>('dashboard');
  return <><p className="eyebrow">УПРАВЛЕНИЕ МАГАЗИНОМ</p><h1>Ваш каталог</h1><p className="admin-intro">Подготовьте товары и управляйте тем, что видят покупатели.</p><dl className="admin-stats">{[['Всего товаров',stats.prompts],['В каталоге',stats.published],['Черновиков',stats.draft],['В архиве',stats.archived]].map(([name,count])=><div key={name}><dt>{name}</dt><dd>{count}</dd></div>)}</dl><section className="admin-next"><h2>Всё начинается с товара</h2><p>Редактируйте описания, назначайте цены и сохраняйте закрытые тексты. Оплата пока не подключена, реальные продажи не выполняются.</p><a className="primary" href="/admin/prompts">Управлять товарами <span>↗</span></a></section></>;
}
