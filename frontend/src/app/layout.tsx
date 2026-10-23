import type { Metadata } from 'next';
import './globals.css';
import './storefront.css';
import './manual-payments.css';
import './neural-hero.css';
import './account-hero.css';
import './account-workspace.css';
import './violet-theme.css';
import './commerce-info.css';
export const metadata: Metadata = {title:'ПромтМаркет | Промпты для ваших задач',description:'Готовые инструкции для AI: программирование, бизнес, маркетинг, изображения и видео.'};
// The same image must respect the preview flag supplied at container startup.
export const dynamic = 'force-dynamic';
export default function RootLayout({children}:Readonly<{children:React.ReactNode}>){return <html lang="ru"><body className="storefront violet-theme">{children}</body></html>;}
