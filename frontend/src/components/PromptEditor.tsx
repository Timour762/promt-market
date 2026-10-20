"use client";
import { useEffect, useState, type FormEvent, type MouseEvent } from 'react';
import { useRouter } from 'next/navigation';
import { adminMutation } from '../lib/admin-client';
import { formatPrice, statusLabels, type AdminPrompt, type Category } from '../lib/admin-types';
type Fields = { id: string; title: string; category_id: string; description: string; result: string; symbol: string; price: string; content: string };
function fieldsFor(prompt: AdminPrompt | null, categories: Category[]): Fields {
 return { id: prompt?.id ?? '', title: prompt?.title ?? '', category_id: String(prompt?.category_id ?? categories[0]?.id ?? ''), description: prompt?.description ?? '', result: prompt?.result ?? '', symbol: prompt?.symbol ?? 'AI', price: prompt?.price_minor == null ? '' : (prompt.price_minor/100).toFixed(2), content: prompt?.content ?? '' };
}
export default function PromptEditor({ initialPrompt, categories }: { initialPrompt: AdminPrompt | null; categories: Category[] }) {
 const router = useRouter();
 const [prompt,setPrompt] = useState(initialPrompt);
 const [fields,setFields] = useState<Fields>(()=>fieldsFor(initialPrompt,categories));
 const [dirty,setDirty] = useState(false); const [pending,setPending] = useState(false);
 const [error,setError] = useState(''); const [message,setMessage] = useState('');
 useEffect(()=>{ if (!dirty) return; const warn=(event:BeforeUnloadEvent)=>{event.preventDefault();event.returnValue='';};window.addEventListener('beforeunload',warn);return ()=>window.removeEventListener('beforeunload',warn);},[dirty]);
 function change(key:keyof Fields,value:string){setFields(previous=>({...previous,[key]:value}));setDirty(true);setMessage('');}
 function back(event:MouseEvent<HTMLAnchorElement>){if (dirty&&!window.confirm('Есть несохранённые изменения. Вернуться к списку без сохранения?'))event.preventDefault();}
 function apply(saved:AdminPrompt){setPrompt(saved);setFields(fieldsFor(saved,categories));setDirty(false);}
 async function save(event:FormEvent<HTMLFormElement>){
  event.preventDefault();if(pending)return;setError('');setMessage('');
  const price=fields.price.trim();let priceMinor:number|null=null;
  if(price){if(!/^\d+(?:[.,]\d{1,2})?$/.test(price)){setError('Введите цену в рублях, например 490 или 490,50.');return;}const [whole,fraction='']=price.replace(',','.').split('.');priceMinor=Number(whole)*100+Number(fraction.padEnd(2,'0'));if(!Number.isSafeInteger(priceMinor)||priceMinor>2147483647){setError('Цена превышает допустимый размер.');return;}}
  const data={title:fields.title,category_id:Number(fields.category_id),description:fields.description,result:fields.result,symbol:fields.symbol,price_minor:priceMinor,content:fields.content};
  setPending(true);
  try{const saved=await adminMutation(prompt?`prompts/${prompt.id}`:'prompts',prompt?'PATCH':'POST',prompt?{...data,revision:prompt.revision}:{...data,id:fields.id});const created=!prompt;apply(saved);setMessage(created?'Черновик создан. Теперь можно подготовить его к публикации.':'Изменения сохранены.');if(created)router.replace(`/admin/prompts/${saved.id}`);router.refresh();}
  catch(cause){setError(cause instanceof Error?cause.message:'Не удалось сохранить товар.');}finally{setPending(false);}
 }
 async function status(action:'publish'|'archive'|'draft'){
  if(!prompt||pending||dirty)return;setError('');setMessage('');setPending(true);
  try{const saved=await adminMutation(`prompts/${prompt.id}/${action}`,'POST',{revision:prompt.revision});apply(saved);setMessage(action==='publish'?'Товар показан в локальном каталоге.':action==='archive'?'Товар перенесён в архив и скрыт из каталога.':'Товар сохранён как черновик и скрыт из каталога.');router.refresh();}
  catch(cause){setError(cause instanceof Error?cause.message:'Не удалось изменить состояние.');}finally{setPending(false);}
 }
 return <><a className="back-link" href="/admin/prompts" onClick={back}>← К товарам</a><div className="admin-heading editor-heading"><div><p className="eyebrow">{prompt?'РЕДАКТИРОВАНИЕ':'НОВЫЙ ПРОМПТ'}</p><h1>{prompt?prompt.title:'Добавить товар'}</h1><p className="admin-intro">Подготовьте карточку для покупателя и сохраните полный текст отдельно.</p></div>{prompt&&<span className={`status-badge ${prompt.status}`}>{statusLabels[prompt.status]}</span>}</div>
 <div className="editor-layout"><form id="prompt-editor" className="prompt-editor" onSubmit={save} onInvalidCapture={event=>{const group=(event.target as HTMLElement).closest('details');if(group)group.open=true;}} aria-busy={pending}>
  <fieldset disabled={pending}>
   <section className="editor-section"><div className="editor-section-heading"><span>01</span><div><h2>Карточка товара</h2><p>Эти данные видны покупателям в каталоге.</p></div></div><label>Название<input value={fields.title} onChange={event=>change('title',event.target.value)} required maxLength={200}/></label><div className="editor-pair"><label>Категория<select value={fields.category_id} onChange={event=>change('category_id',event.target.value)} required>{categories.map(category=><option key={category.id} value={category.id}>{category.name}</option>)}</select></label><label>Цена, ₽<input value={fields.price} onChange={event=>change('price',event.target.value)} inputMode="decimal" placeholder="Пока не назначена" aria-describedby="price-help"/></label></div><p className="field-hint" id="price-help">Пустое поле: цена не назначена. Для публикации задайте цену.</p><label>Краткое описание<textarea value={fields.description} onChange={event=>change('description',event.target.value)} required maxLength={6000} rows={3}/></label><label>Ожидаемый результат<textarea value={fields.result} onChange={event=>change('result',event.target.value)} required maxLength={8000} rows={4}/></label></section>
   <details className="editor-section protected-section"><summary><span>02</span><div><strong>Полный текст промпта</strong><small>{fields.content.length?`${fields.content.length} символов · закрытый текст`:'Пока не добавлен · закрытый текст'}</small></div></summary><div className="editor-disclosure"><p className="field-hint">Текст доступен только администратору. Каждое изменение создаёт новую версию; в публичный каталог он не передаётся.</p><label>Инструкция для AI<textarea className="content-editor" value={fields.content} onChange={event=>change('content',event.target.value)} maxLength={100000} rows={18} spellCheck={false}/></label></div></details>
   <details className="editor-section"><summary><span>03</span><div><strong>Адрес и оформление</strong><small>{fields.id?`/prompts/${fields.id}`:'Задайте адрес нового товара'}</small></div></summary><div className="editor-disclosure"><label>Адрес товара<input value={fields.id} onChange={event=>change('id',event.target.value)} required minLength={2} maxLength={80} pattern="[a-z][a-z0-9-]+" readOnly={!!prompt} aria-describedby="slug-help"/></label><p className="field-hint" id="slug-help">Латинские строчные буквы, цифры и дефис. Адрес задаётся один раз; значение new зарезервировано.</p><label>Обозначение на обложке<input value={fields.symbol} onChange={event=>change('symbol',event.target.value)} required maxLength={20}/></label></div></details>
  </fieldset>
  {error&&<p className="form-error" role="alert">{error}</p>}{message&&<p className="save-message" role="status">{message}</p>}
  <div className="editor-save"><button className="primary" type="submit" disabled={pending||!categories.length}>{pending?'Сохраняем…':prompt?'Сохранить изменения':'Создать черновик'} <span>↗</span></button><span className="field-hint">{dirty?'Есть несохранённые изменения':prompt?'Изменения сохранены':'Новый товар появится сначала в черновиках'}</span></div>
 </form>
 <aside className="editor-sidebar"><h2>Видимость товара</h2><dl><div><dt>Состояние</dt><dd>{prompt?statusLabels[prompt.status]:'Новый черновик'}</dd></div><div><dt>Сохранённая цена</dt><dd>{formatPrice(prompt?.price_minor??null)}</dd></div><div><dt>Версия текста</dt><dd>{prompt?.content_version??0}</dd></div></dl><p>Публикация показывает карточку в локальном каталоге. Полный текст остаётся закрытым.</p>{dirty&&<p className="field-hint">Сначала сохраните изменения, затем меняйте видимость.</p>}{!prompt&&<p className="field-hint">Сначала создайте черновик.</p>}{prompt&&<div className="status-actions">{prompt.status!=='published'&&<button className="secondary-button" disabled={pending||dirty} onClick={()=>status('publish')}>Показать в каталоге</button>}{prompt.status!=='draft'&&<button className="secondary-button" disabled={pending||dirty} onClick={()=>status('draft')}>Перевести в черновик</button>}{prompt.status!=='archived'&&<button className="text-button" disabled={pending||dirty} onClick={()=>status('archive')}>Убрать в архив</button>}{prompt.status==='published'&&<a className="card-link" href={`/prompts/${prompt.id}`} target="_blank" rel="noopener noreferrer">Посмотреть карточку ↗</a>}</div>}</aside></div></>;
}
