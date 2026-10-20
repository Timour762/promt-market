export type Order = { id: string; prompt_id: string; title: string; price_minor: number; currency: string; status: 'pending' | 'awaiting_confirmation' | 'paid' | 'test_granted' | 'sandbox_paid'; created_at: string };
export type LibraryPrompt = Order & { content: string; version: number };
export const orderStatus = { pending: 'Не оплачен', awaiting_confirmation: 'Ожидает подтверждения', paid: 'Оплачен', test_granted: 'Учебный доступ', sandbox_paid: 'Тестовая оплата подтверждена' };
export type PaymentDetails = { order_id: string; status: Order['status']; recipient: { recipient_name: string; bank_name: string; card_number: string } | null };
export type PendingPayment = Order & { customer_name: string; customer_contact: string; requested_at: string; recipient_name: string; bank_name: string; masked_card: string };
export type PendingPayments = { total: number; items: PendingPayment[] };
export function orderPrice(order: Order) { return new Intl.NumberFormat('ru-RU', { style: 'currency', currency: order.currency }).format(order.price_minor / 100); }
