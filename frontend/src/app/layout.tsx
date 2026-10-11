import type { Metadata } from 'next';
import './globals.css';
export const metadata: Metadata = {title:'ПромтМаркет | Промпты для ваших задач',description:'Готовые инструкции для AI: программирование, бизнес, маркетинг, изображения и видео.'};
export default function RootLayout({children}:Readonly<{children:React.ReactNode}>){return <html lang="ru"><body>{children}</body></html>;}
