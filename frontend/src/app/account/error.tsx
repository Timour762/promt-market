"use client";
export default function AccountError({reset}:{reset:()=>void}){return <main className="account-page"><h1>Не удалось загрузить кабинет</h1><p>Сервис временно недоступен. Ваши данные сохранены.</p><button className="primary" type="button" onClick={reset}>Повторить</button></main>;}
