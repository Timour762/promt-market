import 'server-only';

export function isCheckoutAvailable(): boolean {
  return process.env.APP_ENV !== 'production'
    || (process.env.LEGAL_READY === 'true' && process.env.PLATEGA_ENABLED === 'true');
}
