"use client";
import { usePathname } from 'next/navigation';
export default function AccountNav(){const pathname=usePathname();return <nav className="account-nav" aria-label="Личный кабинет">{[['/account','Профиль'],['/account/library','Моя библиотека'],['/account/orders','Мои заказы'],['/catalog','Каталог ↗']].map(([href,title])=><a href={href} key={href} aria-current={(href==='/account'?pathname===href:pathname.startsWith(href))?'page':undefined}>{title}</a>)}</nav>;}
