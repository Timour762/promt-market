"use client";
export default function LoginError({ reset }: { reset: () => void }) { return <main className="empty"><h1>Сервис входа недоступен</h1><button onClick={reset}>Повторить</button><p><a href="/catalog">В каталог</a></p></main>; }
