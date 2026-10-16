import { NextRequest, NextResponse } from 'next/server';
type Context = { params: Promise<{ path: string[] }> };
const allowedOrigins = (process.env.AUTH_ALLOWED_ORIGINS ?? 'http://localhost:3107,http://127.0.0.1:3107').split(',');
async function proxy(request: NextRequest, context: Context) {
  const { path } = await context.params;
  const validPrompt = path[0] === 'prompts' && ((request.method === 'POST' && path.length === 1) || (path.length === 2 && request.method === 'PATCH' && /^[a-z][a-z0-9-]{1,79}$/.test(path[1])) || (path.length === 3 && request.method === 'POST' && /^[a-z][a-z0-9-]{1,79}$/.test(path[1]) && ['publish','archive','draft'].includes(path[2])));
  const valid = validPrompt || (request.method === 'POST' && path.length === 3 && path[0] === 'orders' && /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(path[1]) && path[2] === 'test-access');
  if (!valid) return NextResponse.json({ detail: 'Неизвестное действие' }, { status: 404 });
  const origin = request.headers.get('origin') ?? '';
  if (!allowedOrigins.includes(origin)) return NextResponse.json({ detail: 'Недопустимый источник запроса' }, { status: 403 });
  if (!request.headers.get('content-type')?.startsWith('application/json')) return NextResponse.json({ detail: 'Ожидается JSON' }, { status: 415 });
  const session = request.cookies.get('pm_session')?.value;
  if (!session) return NextResponse.json({ detail: 'Войдите в аккаунт администратора' }, { status: 401 });
  const chunks: Uint8Array[] = []; let size = 0;
  const reader = request.body?.getReader();
  if (!reader) return NextResponse.json({ detail: 'Пустой запрос' }, { status: 400 });
  while (true) {
    const { value, done } = await reader.read(); if (done) break;
    size += value.length;
    if (size > 512000) { await reader.cancel(); return NextResponse.json({ detail: 'Слишком большой текст' }, { status: 413 }); }
    chunks.push(value);
  }
  const body = Buffer.concat(chunks).toString('utf8');
  const csrf = request.cookies.get('pm_csrf')?.value ?? '';
  try {
    const upstream = await fetch(`${process.env.BACKEND_URL ?? 'http://127.0.0.1:8107'}/api/v1/admin/${path.map(encodeURIComponent).join('/')}`, { method: request.method, headers: { 'Content-Type': 'application/json', Origin: origin, Cookie: `pm_session=${encodeURIComponent(session)}; pm_csrf=${encodeURIComponent(csrf)}`, 'X-CSRF-Token': request.headers.get('x-csrf-token') ?? '' }, body, cache: 'no-store', redirect: 'error', signal: AbortSignal.timeout(12000) });
    return new NextResponse(await upstream.text(), { status: upstream.status, headers: { 'Content-Type': 'application/json', 'Cache-Control': 'no-store' } });
  } catch { return NextResponse.json({ detail: 'Сервис каталога временно недоступен' }, { status: 503, headers: { 'Cache-Control': 'no-store' } }); }
}
export const POST = proxy;
export const PATCH = proxy;
