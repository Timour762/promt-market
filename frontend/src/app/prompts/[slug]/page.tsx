import type { Metadata } from 'next';
import { notFound } from 'next/navigation';
import catalog from '../../../data/catalog.json';

type PageProps = { params: Promise<{ slug: string }> };
const inputs: Record<string, string[]> = {
  python: ['Описание задачи и ожидаемое поведение', 'Стек, ограничения и существующий код, если он есть'],
  business: ['Бизнес-идея, регион и целевая аудитория', 'Бюджет, навыки и доступные ресурсы'],
  marketing: ['Продукт, аудитория и рынок', 'Рекламный бюджет и цель продвижения'],
  reels: ['Тема аккаунта, аудитория и платформа', 'Длительность, цель и стиль видео'],
  image: ['Объект, назначение изображения и визуальный стиль', 'Соотношение сторон и выбранный генератор'],
  video: ['Идея, жанр и визуальный стиль', 'Генератор, длительность и соотношение сторон'],
};

export async function generateMetadata({ params }: PageProps): Promise<Metadata> {
  const { slug } = await params;
  const prompt = catalog.find(item => item.id === slug);
  return prompt ? { title: `${prompt.title} | ПромтМаркет`, description: prompt.description } : { title: 'Промпт не найден | ПромтМаркет' };
}

export default async function PromptPage({ params }: PageProps) {
  const { slug } = await params;
  const prompt = catalog.find(item => item.id === slug);
  if (!prompt) notFound();
  const isGenerator = prompt.id === 'image' || prompt.id === 'video';
  return <>
    <a className="skip" href="#prompt-content">Перейти к описанию</a>
    <header>
      <a className="logo" href="/"><span className="mark">п<span>м</span></span>ПромтМаркет<span className="beta">Первая коллекция</span></a>
      <nav aria-label="Навигация"><a href="/catalog">Каталог</a><a href="/catalog#how">Как это работает ↗</a></nav>
    </header>
    <main id="prompt-content" className="product-page">
      <nav className="breadcrumbs" aria-label="Хлебные крошки"><a href="/">Главная</a><span aria-hidden="true">/</span><a href="/catalog">Каталог</a><span aria-hidden="true">/</span><span>{prompt.category}</span></nav>
      <div className="product-layout">
        <article className="product-description">
          <p className="eyebrow">{prompt.category}</p>
          <h1>{prompt.title}</h1>
          <p className="product-lead">{prompt.description}</p>
          <section className="product-section"><h2>Что вы получите</h2><p>{prompt.result}</p><p>Готовую инструкцию с полями для ваших исходных данных. Она помогает задать структуру ответа AI и сформулировать задачу.</p></section>
          <section className="product-section"><h2>Что подготовить</h2><ul>{inputs[prompt.id].map(input => <li key={input}>{input}</li>)}</ul></section>
          <section className="product-section"><h2>Как использовать</h2><ol><li>После покупки откройте полный текст в своей библиотеке.</li><li>Замените поля в квадратных скобках своими данными.</li><li>Вставьте заполненную инструкцию в текстового AI-помощника.</li><li>Уточните ответ при необходимости и проверьте результат.</li></ol>{isGenerator && <p className="usage-note">Этот товар используется в текстовом AI-помощнике для подготовки промптов. Полученные инструкции затем переносятся в выбранный генератор {prompt.id === 'image' ? 'изображений' : 'видео'}.</p>}</section>
          <section className="product-section"><h2>Перед использованием</h2><p>Совместимость с конкретными моделями ещё проверяется. Результат зависит от выбранной модели и ваших исходных данных. Код, расчёты и фактические утверждения в ответе AI нужно проверять.</p></section>
        </article>
        <aside className={`product-summary card ${prompt.id}`} aria-label="Информация о товаре">
          <div className="cover"><span className="cover-label">PROMPT / {String(catalog.indexOf(prompt) + 1).padStart(2, '0')}</span><span className="cover-symbol" aria-hidden="true">{prompt.symbol}</span><span className="cover-bottom">{prompt.category}<span>↗</span></span></div>
          <div className="product-summary-body"><p className="eyebrow">ГОТОВИТСЯ К ЗАПУСКУ</p><h2>Скоро в продаже</h2><p>Цена ещё не назначена. Покупка станет доступна после подключения оплаты.</p><div className="locked-content"><span aria-hidden="true">⌑</span><div><strong>Полный текст закрыт</strong><p>Будет доступен в личной библиотеке после подтверждённой покупки.</p></div></div><a className="primary" href="/catalog">Вернуться в каталог <span>↗</span></a></div>
        </aside>
      </div>
    </main>
    <footer><a className="logo" href="/">ПромтМаркет<span className="footer-dot">.</span></a><span>Инструкции, с которых начинается работа.</span><a href="/catalog">В каталог ↗</a></footer>
  </>;
}