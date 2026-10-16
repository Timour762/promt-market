import 'server-only';
import { cookies } from 'next/headers';
import { redirect, notFound } from 'next/navigation';
export async function accountFetch<T>(path: string): Promise<T> {
  const token = (await cookies()).get('pm_session')?.value;
  if (!token) redirect('/login');
  const response = await fetch(`${process.env.BACKEND_URL ?? 'http://127.0.0.1:8107'}/api/v1/me/${path}`, { headers: { Cookie: `pm_session=${encodeURIComponent(token)}` }, cache: 'no-store', signal: AbortSignal.timeout(10000) });
  if (response.status === 401) redirect('/login');
  if (response.status === 404) notFound();
  if (!response.ok) throw new Error('Account service unavailable');
  return response.json();
}
