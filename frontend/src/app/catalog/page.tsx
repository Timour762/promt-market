import SiteHeader from '../../components/SiteHeader';
import NeuralHero from '../../components/NeuralHero';
import type { Metadata } from 'next';
export const metadata:Metadata={title:'Каталог промптов | ПромтМаркет',description:'Выберите промпт для программирования, бизнеса, маркетинга, изображений и видео.'};
export default function CatalogPage(){
 return <div className="neural-storefront neural-home"><a className="skip" href="/catalog/collection">Перейти к каталогу</a><SiteHeader/><main className="neural-main"><NeuralHero variant="catalog"/></main></div>;
}
