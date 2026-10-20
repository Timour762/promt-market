import { isIP } from 'node:net';

export function trustedClientAddress(headers: Pick<Headers, 'get'>, source = 'caddy'): string | null {
  let address: string;
  if (source === 'render') {
    // Render's edge overwrites CF-Connecting-IP; caller-supplied XFF can survive.
    // https://render.com/articles/host-pocketbase-on-render
    address = headers.get('cf-connecting-ip')?.trim() ?? '';
  } else if (source === 'caddy') {
    // The existing VPS deployment keeps web private behind its Caddy proxy.
    address = headers.get('x-forwarded-for')?.split(',')[0].trim() ?? '';
  } else {
    return null;
  }
  return isIP(address) ? address : null;
}
