export type Order = { id: string; prompt_id: string; title: string; price_minor: number; currency: string; status: 'pending' | 'test_granted' | 'sandbox_paid'; created_at: string };
export type LibraryPrompt = Order & { content: string; version: number };
export const orderStatus = { pending: 'Не оплачен', test_granted: 'Учебный доступ', sandbox_paid: 'Тестовая оплата подтверждена' };
export function orderPrice(order: Order) { return new Intl.NumberFormat('ru-RU', { style: 'currency', currency: order.currency }).format(order.price_minor / 100); }
