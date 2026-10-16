import Image from 'next/image';
export const covers: Record<string, { src: string; alt: string }> = {
  business: { src: '/images/prompts/business-v1.webp', alt: 'Рабочий стол с блокнотом и ноутбуком для планирования бизнеса' },
  python: { src: '/images/prompts/python-v1.webp', alt: 'Рабочее место разработчика с ноутбуком и кодом на экране' },
  marketing: { src: '/images/prompts/marketing-v1.webp', alt: 'Доска идей и цветовые образцы для маркетинговой кампании' },
  reels: { src: '/images/prompts/reels-v1.webp', alt: 'Смартфон на штативе в студии для съёмки коротких видео' },
  image: { src: '/images/prompts/image-v1.webp', alt: 'Творческая студия с композицией из стекла и цифровым изображением' },
  video: { src: '/images/prompts/video-v1.webp', alt: 'Профессиональная кинокамера в студии с мягким светом' },
};
export default function PromptCover({ id, category, label }: { id: string; category: string; label: string }) {
  const cover = covers[id];
  return <div className={`cover${cover ? ' photo-cover' : ''}`}>
    {cover && <Image src={cover.src} alt={cover.alt} fill sizes="(max-width: 720px) calc(100vw - 40px), (max-width: 1000px) 34vw, 450px" quality={85} />}
    <span className="cover-label">{label}</span>
    <span className="cover-bottom">{category}<span aria-hidden="true">↗</span></span>
  </div>;
}
