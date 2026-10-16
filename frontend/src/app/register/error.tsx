"use client";
export default function RegisterError({ reset }: { reset: () => void }) { return <main className="empty"><h1>Сервис регистрации недоступен</h1><button onClick={reset}>Повторить</button><p><a href="/catalog">В каталог</a></p></main>; }
