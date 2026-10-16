import { notFound } from 'next/navigation';
import SiteHeader from '../../../components/SiteHeader';
import StoreFooter from '../../../components/StoreFooter';
import { legalDocuments } from '../../../lib/legal';
export const metadata={title:'Документы | ПромтМаркет',robots:{index:false,follow:false}};
export default async function LegalPage({params}:{params:Promise<{document:string}>}){
 const {document}=await params;
 if(!Object.prototype.hasOwnProperty.call(legalDocuments,document))notFound();
 const doc=legalDocuments[document];
 return <><SiteHeader/><main className="legal-page"><a className="back-link" href="/catalog">← Каталог</a><p className="eyebrow">ДОКУМЕНТЫ ПРОЕКТА · ЧЕРНОВИК</p><h1>{doc.title}</h1><p className="legal-draft">Версия для согласования. Продажи не открыты.</p><nav className="legal-nav" aria-label="Документы">{Object.entries(legalDocuments).map(([key,value])=><a href={`/legal/${key}`} key={key} aria-current={document===key?'page':undefined}>{value.title}</a>)}</nav>{doc.sections.map(section=><section key={section.title}><h2>{section.title}</h2><p>{section.text}</p></section>)}<p>Контакт: <a className="card-link" href="mailto:promtmarket@mail.ru">promtmarket@mail.ru</a></p></main><StoreFooter/></>;
}
