import Image from 'next/image';

export default function AccountHero({ name }: { name: string }) {
  return (
    <section className="account-hero" aria-labelledby="account-hero-title">
      <div className="account-hero-art" aria-hidden="true">
        <Image
          src="/images/hero/account-robot-v1.png"
          alt=""
          fill
          priority
          sizes="(max-width: 700px) 780px, 100vw"
          quality={85}
        />
      </div>
      <div className="account-hero-inner">
        <div className="account-hero-copy">
          <p className="neural-eyebrow"><span /> ВАШЕ ПРОСТРАНСТВО ДЛЯ ИДЕЙ</p>
          <h1 id="account-hero-title">Личный кабинет</h1>
          <p className="account-hero-welcome">Здравствуйте, {name}</p>
          <p className="account-hero-description">Ваш профиль, библиотека промптов и история заказов — всё в одном месте.</p>
          <a className="account-hero-profile-link" href="#account-details">Перейти к профилю <span aria-hidden="true">↓</span></a>
        </div>
      </div>
    </section>
  );
}
