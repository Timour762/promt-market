import Image from 'next/image';
import StoreLinks from './StoreLinks';

export default function NeuralHero({ variant = 'home' }: { variant?: 'home' | 'catalog' }) {
  const isCatalog = variant === 'catalog';

  return (
    <section className="neural-hero" aria-labelledby="neural-hero-title">
      <div className="neural-hero-art" aria-hidden="true">
        <Image
          src="/images/hero/neural-brain-v1.png"
          alt=""
          fill
          priority
          sizes="(max-width: 800px) 800px, 100vw"
          quality={85}
        />
      </div>
      <div className="neural-hero-inner">
        <div className="neural-hero-copy">
          <p className="neural-eyebrow"><span /> ВАШИ ИДЕИ. ВОЗМОЖНОСТИ AI.</p>
          <h1 id="neural-hero-title">
            {isCatalog ? <>Меньше попыток.<br /><span>Больше результата.</span></> : <>Хороший результат<br />начинается с<br /><span>точного промпта.</span></>}
          </h1>
          <p className="neural-hero-description">
            {isCatalog
              ? 'Готовые промпты для работы и творчества. Найдите свой подход к следующей задаче.'
              : 'Готовые инструкции для AI под реальные задачи. Добавьте свой контекст — и переходите от идеи к результату.'}
          </p>
          <div className="neural-hero-actions">
            <a className="neural-button neural-button-primary" href="/catalog/collection">
              {isCatalog ? 'Открыть коллекцию' : 'Найти свой промпт'} <span aria-hidden="true">↗</span>
            </a>
            <a className="neural-button neural-button-secondary" href="/catalog/collection#how">
              Как это работает <span aria-hidden="true">→</span>
            </a>
          </div>
          <p className="neural-hero-caption">Для бизнеса, кода и творчества</p>
          <StoreLinks className="neural-document-links" />
        </div>
      </div>
    </section>
  );
}
