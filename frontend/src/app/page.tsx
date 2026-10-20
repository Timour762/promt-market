import SiteHeader from '../components/SiteHeader';
import NeuralHero from '../components/NeuralHero';

export default function Home(){
return <div className="neural-storefront neural-home"><a className="skip" href="/catalog/collection">Перейти к каталогу</a><SiteHeader/><main className="neural-main"><NeuralHero/></main></div>;
}
