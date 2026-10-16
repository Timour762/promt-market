"use client";
export default function CatalogError({ reset }: { reset: () => void }) {
  return <main className="empty"><h1>Каталог временно недоступен</h1><p>Не удалось загрузить товары. Попробуйте ещё раз.</p><button onClick={reset}>Повторить</button><p><a href="/">На главную</a></p></main>;
}
