"use client";
export default function PromptError({ reset }: { reset: () => void }) {
  return <main className="empty"><h1>Не удалось загрузить промпт</h1><p>Попробуйте ещё раз немного позже.</p><button onClick={reset}>Повторить</button><p><a href="/catalog">В каталог</a></p></main>;
}
