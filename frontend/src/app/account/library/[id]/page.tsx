import { notFound } from 'next/navigation';
import SiteHeader from '../../../../components/SiteHeader';
import AccountNav from '../../../../components/AccountNav';
import { PromptText } from '../../../../components/OrderActions';
import { accountFetch } from '../../../../lib/orders';
import type { LibraryPrompt } from '../../../../lib/order-types';
export const metadata={title:'Текст промпта | ПромтМаркет',robots:{index:false,follow:false}};
export default async function LibraryDetail({params}:{params:Promise<{id:string}>}){
  const {id}=await params;if(!/^[0-9a-f-]{36}$/i.test(id))notFound();
  const prompt=await accountFetch<LibraryPrompt>(`library/${id}`);
  return <><SiteHeader/><main className="account-page"><AccountNav/><p className="eyebrow">МОЯ БИБЛИОТЕКА · ВЕРСИЯ {prompt.version}</p><h1>{prompt.title}</h1><p className="auth-intro">{prompt.status==='sandbox_paid'?'Тестовая оплата подтверждена.':'Учебный доступ.'} Замените поля в квадратных скобках своими данными и вставьте инструкцию в AI-помощника.</p><PromptText content={prompt.content} orderId={id}/><p><a className="card-link" href="/account/library">← Вернуться в библиотеку</a></p></main></>;
}
