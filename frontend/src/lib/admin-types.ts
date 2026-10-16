export type Category = { id: number; name: string; slug: string };
export type PromptSummary = { id: string; title: string; category_id: number; category: string; description: string; result: string; symbol: string; price_minor: number | null; currency: string; status: 'draft' | 'published' | 'archived'; revision: number };
export type AdminPrompt = PromptSummary & { content: string; content_version: number };
export type PromptList = { items: PromptSummary[]; total: number; offset: number; limit: number };
export const statusLabels = { draft: 'Черновик', published: 'В каталоге', archived: 'В архиве' };
export function formatPrice(value: number | null) { return value === null ? 'Не назначена' : new Intl.NumberFormat('ru-RU', { style: 'currency', currency: 'RUB' }).format(value / 100); }
