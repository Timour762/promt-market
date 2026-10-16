"use client";
import { useState } from 'react';
import { useRouter } from 'next/navigation';
export default function PaymentActions({orderId,enabled}:{orderId:string;enabled:boolean}){
  const router=useRouter();const [busy,setBusy]=useState(false);const [message,setMessage]=useState('');
  async function act(action:'start'|'check'){
    setBusy(true);setMessage('');
    try{
      const csrf=await fetch('/api/auth/csrf',{cache:'no-store',signal:AbortSignal.timeout(10000)});
      if(!csrf.ok)throw new Error('Не удалось подготовить запрос');
      const {token}=await csrf.json();
      const response=await fetch(`/api/payments/${orderId}/${action}`,{method:'POST',headers:{'Content-Type':'application/json','X-CSRF-Token':token},body:'{}',signal:AbortSignal.timeout(25000)});
      const data=await response.json();
      if(!response.ok)throw new Error(typeof data.detail==='string'?data.detail:'Не удалось обработать платёж');
      if(action==='start'){
        const url=new URL(data.url);
        if(url.protocol!=='https:'||url.hostname!=='ecomtest.sberbank.ru'||url.username||url.password)throw new Error('Банк вернул неизвестный адрес');
        window.location.assign(url.href);
      }else{setMessage(data.message);router.refresh();}
    }catch(error){setMessage(error instanceof Error?error.message:'Сервис временно недоступен');}finally{setBusy(false);}
  }
  return <section className="payment-actions"><h2>Тестовая оплата через Сбер</h2><p>{enabled?'Тестовый шлюз: реальные деньги не списываются. Способы оплаты на странице банка зависят от настроек тестового магазина.':'Для подключения нужны тестовые данные интернет-эквайринга Сбера. Обычная карта не предоставляет доступ к API. Реальные платежи выключены.'}</p><div className="library-actions"><button type="button" className="primary" disabled={!enabled||busy} onClick={()=>act('start')}>{busy?'Обрабатываем…':'Перейти к тестовой оплате'}</button><button type="button" className="secondary-button" disabled={!enabled||busy} onClick={()=>act('check')}>Проверить оплату</button></div><p role="status" aria-live="polite">{message}</p></section>;
}
