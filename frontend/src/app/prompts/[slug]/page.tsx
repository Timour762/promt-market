import PromptGuide from '../../../components/PromptGuide';
import { promptGuides } from '../../../lib/prompt-guides';
import Image from 'next/image';
import { covers } from '../../../components/PromptCover';
import StoreFooter from '../../../components/StoreFooter';
import PromptCover from '../../../components/PromptCover';
import { OrderButton } from '../../../components/OrderActions';
import SiteHeader from '../../../components/SiteHeader';
import type { Metadata } from 'next';
import { notFound } from 'next/navigation';
import { getPrompt } from '../../../lib/catalog';

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
  const prompt = await getPrompt(slug);
  return prompt ? { title: `${prompt.title} | ПромтМаркет`, description: prompt.description } : { title: 'Промпт не найден | ПромтМаркет' };
}

export default async function PromptPage({ params }: PageProps) {
  const { slug } = await params;
  const prompt = await getPrompt(slug);
  if (!prompt) notFound();
  const isGenerator = prompt.id === 'image' || prompt.id === 'video';
  const cover=covers[prompt.id];
  return <><a className="skip" href="#prompt-content">Перейти к описанию</a><SiteHeader/><main id="prompt-content" className="product-page"><nav className="breadcrumbs" aria-label="Хлебные крошки"><a href="/">Главная</a><span aria-hidden="true">/</span><a href="/catalog">Каталог</a><span aria-hidden="true">/</span><span>{prompt.category}</span></nav>
    <article className="pv-product store-product"><div className="pv-product-image">{cover?<Image src={cover.src} alt={cover.alt} fill sizes="(max-width:800px) calc(100vw - 48px), 650px" quality={90}/>:<PromptCover id={prompt.id} category={prompt.category} label="ГОТОВАЯ ИНСТРУКЦИЯ"/>}</div><div className="pv-product-body"><p className="pv-kicker">{prompt.category} / Готовая инструкция</p><h1>{prompt.title}</h1><p className="pv-product-lead">{prompt.description}</p><div className="pv-result"><span>Вы получите</span><h2>{prompt.result}</h2><p>Готовую инструкцию с полями для ваших исходных данных. Она помогает задать структуру ответа AI и сформулировать задачу.</p></div><div className="store-product-price"><strong>{prompt.price_minor===null?'Скоро в продаже':new Intl.NumberFormat('ru-RU',{style:'currency',currency:prompt.currency}).format(prompt.price_minor/100)}</strong><span>{prompt.price_minor===null?'Цена ещё не назначена':'За готовую инструкцию'}</span></div>{prompt.price_minor!==null?<OrderButton promptId={prompt.id}/>:<a className="primary" href="/catalog">Выбрать другой промпт ↗</a>}<p className="pv-caption">Полный текст появится в вашей библиотеке после подтверждения оплаты.</p></div></article>
    {promptGuides[prompt.id]&&<PromptGuide guide={promptGuides[prompt.id]}/>}
    <div className="store-product-details"><section className="product-section"><p className="pv-kicker">01 / ПОДГОТОВКА</p><h2>Что подготовить</h2><ul>{(inputs[prompt.id]??['Описание вашей задачи','Исходные данные и ограничения']).map(input=><li key={input}>{input}</li>)}</ul></section><section className="product-section"><p className="pv-kicker">02 / ИСПОЛЬЗОВАНИЕ</p><h2>Как использовать</h2><ol><li>После выдачи доступа откройте полный текст в своей библиотеке.</li><li>Замените поля в квадратных скобках своими данными.</li><li>Вставьте заполненную инструкцию в текстового AI-помощника.</li><li>Уточните ответ при необходимости и проверьте результат.</li></ol>{isGenerator&&<p className="usage-note">Этот товар используется в текстовом AI-помощнике для подготовки промптов. Полученные инструкции затем переносятся в выбранный генератор {prompt.id==='image'?'изображений':'видео'}.</p>}</section><section className="product-section"><p className="pv-kicker">03 / ПЕРЕД НАЧАЛОМ</p><h2>Перед использованием</h2><p>Совместимость с конкретными моделями ещё проверяется. Результат зависит от выбранной модели и ваших исходных данных. Код, расчёты и фактические утверждения в ответе AI нужно проверять.</p></section></div></main><StoreFooter/></>;
}
