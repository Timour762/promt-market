import { getCurrentUser } from '../lib/auth';
import StoreArrow from './StoreArrow';
export default async function SiteHeader(){
 const user=await getCurrentUser().catch(()=>null);
 return <header className="pv-header"><a className="pv-logo" href="/" aria-label="ПромтМаркет, главная"><span className="pv-mark">пм<span/></span><span>Промт<span className="pv-logo-light">Маркет</span></span></a><nav aria-label="Основная навигация"><a href="/catalog">Каталог</a><a className="how-link" href="/catalog#how">Как это работает</a>{user?.role==='admin'&&<a className="admin-header-link" href="/admin">Управление</a>}</nav><a className="pv-account" href={user?'/account':'/login'}><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" aria-hidden="true"><circle cx="12" cy="8" r="3.5"/><path d="M5 21v-2a7 7 0 0 1 14 0v2"/></svg><span>{user?'Личный кабинет':'Войти'}</span></a></header>;
}
