import json
from urllib.request import Request,build_opener,HTTPRedirectHandler
from urllib.error import URLError
from urllib.parse import urlsplit
from starlette.concurrency import run_in_threadpool
from fastapi import HTTPException
from app.core.config import get_settings

BASE="https://ecomtest.sberbank.ru/ecomm/gw/partner/api/v1/"
class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self,*args,**kwargs): return None

def enabled():
    s=get_settings()
    return bool(s.sber_sandbox_enabled and s.sber_username and s.sber_password and s.sber_password.get_secret_value())
def safe_form_url(value):
    if not isinstance(value,str):return None
    parts=urlsplit(value)
    if parts.scheme=="https" and parts.hostname=="ecomtest.sberbank.ru" and parts.port in (None,443) and not parts.username and not parts.password:
        return value
    return None
async def call(method,data):
    if not enabled():raise HTTPException(503,"Нужны тестовые данные эквайринга Сбера. Реальная оплата выключена.")
    settings=get_settings()
    payload={**data,"userName":settings.sber_username,"password":settings.sber_password.get_secret_value()}
    def send():
        request=Request(BASE+method,data=json.dumps(payload).encode(),headers={"Content-Type":"application/json","Accept":"application/json"},method="POST")
        try:
            with build_opener(NoRedirect()).open(request,timeout=10) as response:
                raw=response.read(262145)
                if len(raw)>262144:raise ValueError()
                result=json.loads(raw)
                if not isinstance(result,dict):raise ValueError()
                return result
        except (URLError,TimeoutError,ValueError,OSError):
            raise HTTPException(503,"Тестовый шлюз Сбера не ответил. Повторите проверку статуса; новый платёж не создаётся.") from None
    return await run_in_threadpool(send)
