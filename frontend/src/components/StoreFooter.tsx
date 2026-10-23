import StoreLinks from './StoreLinks';
import { shopContact } from '../lib/legal';

export default function StoreFooter() {
  return <footer className="store-footer">
    <div className="store-footer-identity"><a className="store-footer-brand" href="/">ПромтМаркет</a><a className="store-support-email" href={`mailto:${shopContact.email}`}>{shopContact.email}</a></div>
    <StoreLinks />
    <a className="store-refunds-link" href="/legal/refunds">Обращения и возвраты</a>
  </footer>;
}
