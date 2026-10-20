import { NextRequest, NextResponse } from 'next/server';

export async function POST(request: NextRequest) {
  const headers = { 'Cache-Control': 'no-store' };
  if (request.headers.get('content-type')?.split(';')[0].trim().toLowerCase() !== 'application/json') return NextResponse.json({ detail: 'Expected JSON' }, { status: 415, headers });
  const chunks: Uint8Array[] = []; let size = 0;
  const reader = request.body?.getReader();
  if (!reader) return NextResponse.json({ detail: 'Empty callback' }, { status: 400, headers });
  while (true) {
    const { value, done } = await reader.read(); if (done) break;
    size += value.length;
    if (size > 8192) { await reader.cancel(); return NextResponse.json({ detail: 'Callback too large' }, { status: 413, headers }); }
    chunks.push(value);
  }
  try {
    const upstream = await fetch(`${process.env.BACKEND_URL ?? 'http://127.0.0.1:8107'}/api/v1/payments/platega/webhook`, {
      method: 'POST', headers: { 'Content-Type': 'application/json', 'X-MerchantId': request.headers.get('X-MerchantId') ?? '', 'X-Secret': request.headers.get('X-Secret') ?? '' },
      body: Buffer.concat(chunks).toString('utf8'), cache: 'no-store', redirect: 'error', signal: AbortSignal.timeout(20000),
    });
    return new NextResponse(await upstream.text(), { status: upstream.status, headers: { ...headers, 'Content-Type': 'application/json' } });
  } catch { return NextResponse.json({ detail: 'Retry callback later' }, { status: 503, headers }); }
}
