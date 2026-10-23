export default function StoreLinks({ className }: { className?: string }) {
  return <nav className={className} aria-label="Документы и поддержка">
    <a href="/legal/privacy">Политика конфиденциальности</a>
    <a href="/legal/terms">Пользовательское соглашение</a>
    <a href="/pricing">Цены и тарифы</a>
    <a href="/legal/contacts">Поддержка</a>
  </nav>;
}
