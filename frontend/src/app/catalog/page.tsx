import type { Metadata } from 'next';
import PromptCatalog from '../../components/PromptCatalog';
export const metadata: Metadata = {
  title: 'Каталог промптов | ПромтМаркет',
  description: 'Выберите промпт для программирования, бизнеса, маркетинга, изображений и видео.',
};
export default function CatalogPage() {
  return <>
    <a className="skip" href="#catalog">Перейти к каталогу</a>
    <header>
      <a className="logo" href="/"><span className="mark">п<span>м</span></span>ПромтМаркет<span className="beta">Первая коллекция</span></a>
      <nav aria-label="Навигация"><a href="/catalog" aria-current="page">Каталог</a><a href="#how">Как это работает ↗</a></nav>
    </header>
    <main className="catalog-page">
      <div className="catalog-intro">
        <a className="back-link" href="/">← Главная</a>
        <h1>Каталог промптов</h1>
        <p>Найдите готовую инструкцию для своей задачи.</p>
      </div>
      <PromptCatalog/>
<section id="how" className="how"><div><p className="eyebrow">ПОНЯТНЫЙ ПУТЬ</p><h2>Не нужно начинать<br/>с пустой строки.</h2><p>Промпт задаёт структуру работы.<br/>Контекст и решения остаются за вами.</p></div><ol>{[['Выберите задачу','Изучите описание и ожидаемый результат.'],['Добавьте свой контекст','Заполните исходные данные в инструкции.'],['Работайте с AI','Используйте ответ как основу и проверяйте факты.']].map(([title,text],i)=><li key={title}><span>0{i+1}</span><div><h3>{title}</h3><p>{text}</p></div></li>)}</ol></section>
      <aside className="launch-note">Предварительный каталог. Оплата не подключена, платные тексты не опубликованы.</aside>
    </main>
    <footer><a className="logo" href="/">ПромтМаркет<span className="footer-dot">.</span></a><span>Инструкции, с которых начинается работа.</span><a href="#catalog">К коллекции ↑</a></footer>
  </>;
}
