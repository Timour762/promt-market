import PromptEditor from '../../../../components/PromptEditor';
import { adminFetch } from '../../../../lib/admin';
import type { Category } from '../../../../lib/admin-types';
export default async function NewPromptPage() {
 const categories = await adminFetch<Category[]>('categories');
 return <PromptEditor initialPrompt={null} categories={categories}/>;
}
