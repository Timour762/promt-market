import 'server-only';
import { cookies } from 'next/headers';
import { notFound, redirect } from 'next/navigation';
import { getCurrentUser } from './auth';
export async function requireAdmin() {
  const user = await getCurrentUser();
  if (!user) redirect('/login');
  if (user.role !== 'admin') redirect('/account');
  return user;
}
export async function adminFetch<T>(path: string): Promise<T> {
  const token = (await cookies()).get('pm_session')?.value;
  if (!token) redirect('/login');
  const response = await fetch(`${process.env.BACKEND_URL ?? 'http://127.0.0.1:8107'}/api/v1/admin/${path}`, { headers: { Cookie: `pm_session=${encodeURIComponent(token)}` }, cache: 'no-store', signal: AbortSignal.timeout(10000) });
  if (response.status === 401) redirect('/login');
  if (response.status === 403) redirect('/account');
  if (response.status === 404) notFound();
  if (!response.ok) throw new Error('Admin service unavailable');
  return response.json();
}
