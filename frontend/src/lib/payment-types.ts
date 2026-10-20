import type { Order } from './order-types';

export type PlategaPaymentInfo = {
  order_id: string; status: Order['status']; provider: 'platega'; enabled: boolean;
  provider_status: string | null; checkout_url: string | null;
};
export type PlategaSetup = {
  provider: 'platega'; live_enabled: boolean; enabled_in_settings: boolean;
  merchant_id_configured: boolean; secret_configured: boolean; credentials_configured: boolean;
  public_url_configured: boolean; connection_verified: boolean; automatic_confirmation_enabled: boolean;
  webhook_path: string; webhook_url: string | null; checkout_currency: 'RUB'; settlement_currency: 'USDT';
};

export function safePlategaUrl(value: unknown): string | null {
  if (typeof value !== 'string' || /[\s\\]/.test(value)) return null;
  try {
    const url = new URL(value);
    return url.protocol === 'https:' && url.hostname === 'pay.platega.io' && !url.username && !url.password && (!url.port || url.port === '443') ? url.href : null;
  } catch { return null; }
}

export async function paymentMutation(orderId: string, action: 'start' | 'check'): Promise<PlategaPaymentInfo> {
  const csrf = await fetch('/api/auth/csrf', { cache: 'no-store', signal: AbortSignal.timeout(10000) });
  if (!csrf.ok) throw new Error('Не удалось подготовить запрос. Попробуйте ещё раз.');
  const { token } = await csrf.json();
  const response = await fetch(`/api/payments/${orderId}/${action}`, {
    method: 'POST', headers: { 'Content-Type': 'application/json', 'X-CSRF-Token': token },
    body: '{}', signal: AbortSignal.timeout(20000),
  });
  const result = await response.json();
  if (!response.ok) throw new Error(typeof result.detail === 'string' ? result.detail : 'Не удалось обработать платёж. Попробуйте позже.');
  return result;
}
