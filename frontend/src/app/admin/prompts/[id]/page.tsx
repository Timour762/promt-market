import PromptEditor from '../../../../components/PromptEditor';
import { adminFetch } from '../../../../lib/admin';
import type { AdminPrompt, Category } from '../../../../lib/admin-types';
export default async function EditPromptPage({ params }: { params: Promise<{ id: string }> }) {
 const { id } = await params;
 const [prompt,categories] = await Promise.all([adminFetch<AdminPrompt>(`prompts/${encodeURIComponent(id)}`),adminFetch<Category[]>('categories')]);
 return <PromptEditor initialPrompt={prompt} categories={categories}/>;
}
