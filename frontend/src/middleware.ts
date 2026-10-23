import { NextRequest, NextResponse } from 'next/server';
import { isPublicPreview } from './lib/public-preview';

export function middleware(request: NextRequest) {
  if (!isPublicPreview()) return NextResponse.next();

  const headers = { 'Cache-Control': 'no-store', 'X-Robots-Tag': 'noindex, nofollow' };
  if (request.method !== 'GET' && request.method !== 'HEAD') {
    return NextResponse.json({ error: 'public_preview_read_only' }, { status: 503, headers });
  }

  const path = request.nextUrl.pathname;
  const publicPage = ['/', '/catalog', '/catalog/collection', '/pricing', '/preview', '/api/ready'].includes(path)
    || /^\/prompts\/[a-z0-9][a-z0-9-]*$/.test(path)
    || /^\/legal\/(privacy|terms|offer|refunds|license|contacts)$/.test(path);
  const publicAsset = path.startsWith('/_next/static/') || path === '/_next/image'
    || /^\/images\/[a-zA-Z0-9/_-]+\.(png|webp)$/.test(path)
    || /^\/fonts\/[a-zA-Z0-9_-]+\.(ttf|txt)$/.test(path);
  if (publicPage || publicAsset) {
    const response = NextResponse.next();
    response.headers.set('X-Robots-Tag', 'noindex, nofollow');
    return response;
  }
  if (path === '/api' || path.startsWith('/api/')) {
    return NextResponse.json({ error: 'not_available_in_preview' }, { status: 404, headers });
  }
  // The supervisor derives this trusted HTTPS origin from Render at startup.
  const destination = new URL('/preview', process.env.PUBLIC_WEB_URL || request.url);
  return NextResponse.redirect(destination, { status: 307, headers });
}

export const config = { matcher: '/:path*' };
