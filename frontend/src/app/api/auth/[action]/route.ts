import { createHmac } from 'node:crypto';
import { NextRequest, NextResponse } from 'next/server';
import { trustedClientAddress } from '../../../../lib/client-ip';
const backend = process.env.BACKEND_URL ?? 'http://127.0.0.1:8107';
const origins = (process.env.AUTH_ALLOWED_ORIGINS ?? 'http://localhost:3107,http://127.0.0.1:3107').split(',');
type Context = { params: Promise<{ action: string }> };

async function proxy(request: NextRequest, context: Context) {
  const { action } = await context.params;
  if (!(request.method === 'GET' && action === 'csrf') && !(request.method === 'POST' && ['register', 'login', 'logout', 'forgot-password', 'reset-password', 'verify-email', 'resend-verification'].includes(action))) {
    return NextResponse.json({ detail: 'Неизвестное действие' }, { status: 404 });
  }
  const headers = new Headers();
  // Forward only the two cookies owned by this application.
  headers.set('cookie', ['pm_session', 'pm_csrf'].flatMap(name => {
    const value = request.cookies.get(name)?.value;
    return value ? [`${name}=${encodeURIComponent(value)}`] : [];
  }).join('; '));
  let body: string | undefined;
  if (request.method === 'POST') {
    const origin = request.headers.get('origin') ?? '';
    if (!origins.includes(origin)) return NextResponse.json({ detail: 'Недопустимый источник запроса' }, { status: 403 });
    if (!request.headers.get('content-type')?.startsWith('application/json')) return NextResponse.json({ detail: 'Ожидается JSON' }, { status: 415 });
    const reader = request.body?.getReader();
    if (!reader) return NextResponse.json({ detail: 'Пустой запрос' }, { status: 400 });
    const chunks: Uint8Array[] = []; let size = 0;
    while (true) {
      const { value, done } = await reader.read(); if (done) break;
      size += value.length;
      if (size > 8192) { await reader.cancel(); return NextResponse.json({ detail: 'Слишком большой запрос' }, { status: 413 }); }
      chunks.push(value);
    }
    body = Buffer.concat(chunks).toString('utf8');
    const proxySecret = process.env.AUTH_PROXY_SECRET;
    if (proxySecret) {
      const address = trustedClientAddress(request.headers, process.env.AUTH_CLIENT_IP_SOURCE ?? 'caddy');
      if (!address) return NextResponse.json({ detail: 'Не удалось определить источник запроса' }, { status: 503 });
      const identity = createHmac('sha256', proxySecret).update(address).digest('hex');
      const signature = createHmac('sha256', proxySecret).update(`pm-client:${identity}`).digest('hex');
      headers.set('x-pm-client', identity);
      headers.set('x-pm-proxy-signature', signature);
    }
    headers.set('origin', origin);
    headers.set('content-type', 'application/json');
    headers.set('x-csrf-token', request.headers.get('x-csrf-token') ?? '');
  }
  try {
    const upstream = await fetch(`${backend}/api/v1/auth/${action}`, { method: request.method, headers, body, cache: 'no-store', redirect: 'error', signal: AbortSignal.timeout(12000) });
    const result = new NextResponse(upstream.status === 204 ? null : await upstream.text(), { status: upstream.status });
    result.headers.set('Cache-Control', 'no-store');
    result.headers.set('Content-Type', 'application/json');
    for (const cookie of upstream.headers.getSetCookie()) result.headers.append('Set-Cookie', cookie);
    const retry = upstream.headers.get('retry-after');
    if (retry) result.headers.set('Retry-After', retry);
    return result;
  } catch {
    return NextResponse.json({ detail: 'Сервис аккаунтов временно недоступен' }, { status: 503, headers: { 'Cache-Control': 'no-store' } });
  }
}
export const GET = proxy;
export const POST = proxy;
