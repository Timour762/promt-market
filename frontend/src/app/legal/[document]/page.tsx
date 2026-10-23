import type { Metadata } from 'next';
import { notFound } from 'next/navigation';
import SiteHeader from '../../../components/SiteHeader';
import StoreFooter from '../../../components/StoreFooter';
import { legalDocuments, legalRevision, shopContact } from '../../../lib/legal';
import { previewLegalDocuments } from '../../../lib/preview-legal';
import { isPublicPreview } from '../../../lib/public-preview';

type Props = { params: Promise<{ document: string }> };
function getDocument(document: string) {
  const documents = isPublicPreview() ? previewLegalDocuments : legalDocuments;
  return Object.prototype.hasOwnProperty.call(documents, document) ? documents[document] : null;
}

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const doc = getDocument((await params).document);
  return { title: `${doc?.title ?? 'Документ не найден'} | ПромтМаркет`, robots: { index: false, follow: false } };
}

export default async function LegalPage({ params }: Props) {
  const { document } = await params;
  const doc = getDocument(document);
  if (!doc) notFound();
  const documents = isPublicPreview() ? previewLegalDocuments : legalDocuments;
  return <><SiteHeader /><main className="legal-page">
    <a className="back-link" href="/catalog/collection">← Каталог</a>
    <p className="eyebrow">ПРОМТМАРКЕТ · ДОКУМЕНТЫ</p>
    <h1>{doc.title}</h1>
    <p className="legal-revision">Редакция от <time dateTime="2026-10-23">{legalRevision}</time> · {shopContact.website}</p>
    {doc.draft && <p className="legal-draft">Условия платного приобретения для согласования. Реальная оплата пока отключена.</p>}
    <nav className="legal-nav" aria-label="Документы">
      {Object.entries(documents).map(([key, value]) => <a href={`/legal/${key}`} key={key} aria-current={document === key ? 'page' : undefined}>{value.title}</a>)}
      <a href="/pricing">Цены и тарифы</a>
    </nav>
    {document === 'contacts' && <aside className="support-contact"><p>Напишите в поддержку</p><a href={`mailto:${shopContact.email}`}>{shopContact.email}</a><span>Вопросы о товарах, аккаунте и заказах</span></aside>}
    {doc.sections.map(section => <section key={section.title}><h2>{section.title}</h2><p>{section.text}</p></section>)}
    <p>Поддержка: <a className="card-link" href={`mailto:${shopContact.email}`}>{shopContact.email}</a></p>
  </main><StoreFooter /></>;
}
