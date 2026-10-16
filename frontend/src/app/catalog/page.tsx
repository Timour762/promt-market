import SiteHeader from '../../components/SiteHeader';
import StoreFooter from '../../components/StoreFooter';
import PromptCatalog from '../../components/PromptCatalog';
import { getCatalog } from '../../lib/catalog';
import type { Metadata } from 'next';
export const metadata:Metadata={title:'Каталог промптов | ПромтМаркет',description:'Выберите промпт для программирования, бизнеса, маркетинга, изображений и видео.'};
export default async function CatalogPage(){
 const catalog=await getCatalog();
 return <><a className="skip" href="#catalog">Перейти к каталогу</a><SiteHeader/><main className="pv-main catalog-page"><section className="pv-intro"><div><p className="pv-kicker"><span/>БИБЛИОТЕКА ПРАКТИЧНЫХ ИДЕЙ</p><h1>Меньше попыток.<br/><span>Больше результата.</span></h1></div><div className="pv-intro-side"><p>Готовые промпты для работы<br/>и творчества. Найдите свой подход<br/>к следующей задаче.</p><a href="#catalog">Открыть коллекцию <span>↓</span></a></div></section><PromptCatalog catalog={catalog}/><section className="pv-how" id="how"><div><p className="pv-kicker">ОТ ИДЕИ К ДЕЙСТВИЮ</p><h2>Хороший ответ<br/>начинается с вас.</h2></div><ol>{[['Найдите свой промпт','Выберите задачу и изучите ожидаемый результат.'],['Добавьте контекст','Замените поля в инструкции своими данными.'],['Переходите к работе','Используйте ответ как основу и проверяйте факты.']].map(([title,text],i)=><li key={title}><span>0{i+1}</span><div><h3>{title}</h3><p>{text}</p></div></li>)}</ol></section><aside className="launch-note">Предварительный каталог. Реальные платежи пока не подключены.</aside></main><StoreFooter/></>;
}
