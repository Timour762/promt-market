import 'server-only';
import { cookies } from 'next/headers';
import { isPublicPreview } from './public-preview';
export type PublicUser = { id: string; name: string; email: string | null; username: string | null; role: string; email_verified: boolean };
export async function getCurrentUser(): Promise<PublicUser | null> {
  if (isPublicPreview()) return null;
  const token = (await cookies()).get('pm_session')?.value;
  if (!token) return null;
  const response = await fetch(`${process.env.BACKEND_URL ?? 'http://127.0.0.1:8107'}/api/v1/me`, {
    headers: { Cookie: `pm_session=${encodeURIComponent(token)}` }, cache: 'no-store', signal: AbortSignal.timeout(8000),
  });
  if (response.status === 401) return null;
  if (!response.ok) throw new Error('Account unavailable');
  return response.json();
}
