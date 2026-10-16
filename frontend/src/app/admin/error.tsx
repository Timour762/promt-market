"use client";
export default function AdminError({ reset }: { reset: () => void }) { return <div className="empty"><h1>Управление временно недоступно</h1><p>Не удалось получить данные. Попробуйте ещё раз.</p><button onClick={reset}>Повторить</button><p><a href="/account">Личный кабинет</a></p></div>; }
