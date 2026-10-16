import 'server-only';
export type PublicPrompt = { id: string; title: string; category: string; description: string; symbol: string; result: string; price_minor: number | null; currency: string };
const apiUrl = process.env.BACKEND_URL ?? 'http://127.0.0.1:8107';
export async function getCatalog(): Promise<PublicPrompt[]> {
  const response = await fetch(`${apiUrl}/api/v1/prompts`, { cache: 'no-store' });
  if (!response.ok) throw new Error('Catalog unavailable');
  return response.json();
}
export async function getPrompt(slug: string): Promise<PublicPrompt | null> {
  const response = await fetch(`${apiUrl}/api/v1/prompts/${encodeURIComponent(slug)}`, { cache: 'no-store' });
  if (response.status === 404) return null;
  if (!response.ok) throw new Error('Catalog unavailable');
  return response.json();
}
