import asyncio
import secrets
import tempfile
import unittest
from datetime import datetime,timedelta,timezone
from uuid import uuid4
from unittest.mock import patch,AsyncMock,MagicMock
import httpx
from sqlalchemy import select,text,func
from sqlalchemy.ext.asyncio import create_async_engine,async_sessionmaker
from sqlalchemy.pool import NullPool
from app.main import app
from app.db.base import Base
from app.db.session import get_session
from app.core.config import get_settings
from app.auth.models import User,Role,Session
from app.auth.recovery_models import AuthToken
from app.auth.security import password_hasher,token_hash,_attempts
from app.catalog.models import Category,Prompt,PromptVersion
from app.orders.models import Order
from app.payments.models import Payment
from app.admin.models import AuditLog

ORIGIN="http://localhost:3107"
class SecurityFixture(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.schema="pm_test_"+secrets.token_hex(8)
        self.control=create_async_engine(get_settings().database_url,poolclass=NullPool)
        async with self.control.begin() as conn:
            await conn.execute(text('CREATE SCHEMA "'+self.schema+'"'))
        self.engine=create_async_engine(get_settings().database_url,poolclass=NullPool,connect_args={"server_settings":{"search_path":self.schema}})
        self.factory=async_sessionmaker(self.engine,expire_on_commit=False)
        async with self.engine.begin() as conn:await conn.run_sync(Base.metadata.create_all)
        async def database():
            async with self.factory() as db:yield db
        app.dependency_overrides[get_session]=database
        self.patches=[patch('app.auth.router.deliver_local_mail',new=AsyncMock()),patch('app.auth.recovery_router.deliver_local_mail',new=AsyncMock())]
        for item in self.patches:item.start()
        _attempts.clear()
        self.password=secrets.token_urlsafe(24)
        async with self.factory() as db:
            customer=Role(code="customer");admin=Role(code="admin");db.add_all([customer,admin]);await db.flush()
            db.add(User(name="Fixture Admin",username="fixtureadmin",password_hash=password_hasher.hash(self.password),role_id=admin.id,status="active"))
            category=Category(slug="fixture",name="Fixture");db.add(category);await db.flush()
            db.add(Prompt(id="fixture-prompt",title="Fixture prompt",description="Public description",result="Public result",symbol="X",category_id=category.id,price_minor=29900,currency="RUB",status="published"));await db.flush()
            version=PromptVersion(prompt_id="fixture-prompt",version=1,content="PRIVATE_TEST_CONTENT");db.add(version);await db.commit()
        self.client=httpx.AsyncClient(transport=httpx.ASGITransport(app=app),base_url=ORIGIN)
    async def asyncTearDown(self):
        await self.client.aclose()
        app.dependency_overrides.clear()
        for item in self.patches:item.stop()
        await self.engine.dispose()
        async with self.control.begin() as conn:
            await conn.execute(text('DROP SCHEMA "'+self.schema+'" CASCADE'))
        await self.control.dispose()
    async def post(self,client,path,data):
        token=(await client.get('/api/v1/auth/csrf')).json()['token']
        return await client.post(path,json=data,headers={"Origin":ORIGIN,"X-CSRF-Token":token})
    async def register(self,client,email='fixture@example.com'):
        response=await self.post(client,'/api/v1/auth/register',{"email":email,"password":self.password,"name":"Fixture"})
        self.assertEqual(response.status_code,201,response.text)
        return response.json()
    async def admin(self):
        client=httpx.AsyncClient(transport=httpx.ASGITransport(app=app),base_url=ORIGIN)
        response=await self.post(client,'/api/v1/auth/login',{"email":"fixtureadmin","password":self.password})
        self.assertEqual(response.status_code,200,response.text)
        return client
class SecurityTests(SecurityFixture):
    async def test_public_content_and_csrf(self):
        response=await self.client.get('/api/v1/prompts')
        self.assertEqual(response.status_code,200)
        self.assertNotIn('PRIVATE_TEST_CONTENT',response.text)
        self.assertNotIn('content',response.json()[0])
        response=await self.client.post('/api/v1/auth/login',json={"email":"fixtureadmin","password":self.password})
        self.assertEqual(response.status_code,403)
        token=(await self.client.get('/api/v1/auth/csrf')).json()['token']
        response=await self.client.post('/api/v1/auth/login',json={"email":"fixtureadmin","password":self.password},headers={"Origin":"https://evil.invalid","X-CSRF-Token":token})
        self.assertEqual(response.status_code,403)
    async def test_registration_roles_and_reset_revokes_sessions(self):
        user=await self.register(self.client)
        self.assertEqual(user['role'],'customer')
        self.assertEqual((await self.client.get('/api/v1/admin/prompts')).status_code,403)
        response=await self.post(self.client,'/api/v1/auth/register',{"email":"second@example.com","password":self.password,"name":"Fixture","role":"admin"})
        self.assertEqual(response.status_code,422)
        reset=secrets.token_urlsafe(48)
        async with self.factory() as db:
            db.add(AuthToken(token_hash=token_hash(reset),user_id=__import__('uuid').UUID(user['id']),purpose='reset_password',expires_at=datetime.now(timezone.utc)+timedelta(minutes=10)));await db.commit()
        self.assertEqual((await self.post(self.client,'/api/v1/auth/reset-password',{"token":reset,"password":secrets.token_urlsafe(24)})).status_code,200)
        self.assertEqual((await self.client.get('/api/v1/me')).status_code,401)
        self.assertEqual((await self.post(self.client,'/api/v1/auth/reset-password',{"token":reset,"password":self.password})).status_code,400)
    async def test_order_ownership_retry_and_version_snapshot(self):
        await self.register(self.client)
        response=await self.post(self.client,'/api/v1/me/orders',{"prompt_id":"fixture-prompt","price_minor":1})
        self.assertEqual(response.status_code,422)
        order=(await self.post(self.client,'/api/v1/me/orders',{"prompt_id":"fixture-prompt"})).json()
        again=(await self.post(self.client,'/api/v1/me/orders',{"prompt_id":"fixture-prompt"})).json()
        self.assertEqual(order['id'],again['id']);self.assertEqual(order['price_minor'],29900)
        self.assertEqual((await self.client.get('/api/v1/me/library/'+order['id'])).status_code,404)
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app),base_url=ORIGIN) as other:
            await self.register(other,'other@example.com')
            self.assertEqual((await other.get('/api/v1/me/orders/'+order['id'])).status_code,404)
            self.assertEqual((await other.get('/api/v1/me/library/'+order['id']+'/download')).status_code,404)
        async with self.factory() as db:
            prompt=await db.get(Prompt,'fixture-prompt');prompt.price_minor=59900;prompt.status='archived'
            db.add(PromptVersion(prompt_id=prompt.id,version=2,content='NEW_PRIVATE_CONTENT'));await db.commit()
        admin=await self.admin()
        try:
            with patch('app.orders.router.test_access_enabled',return_value=True):
                grant=await self.post(admin,'/api/v1/admin/orders/'+order['id']+'/test-access',{})
                self.assertEqual(grant.status_code,200,grant.text)
        finally:
            await admin.aclose()
        content=await self.client.get('/api/v1/me/library/'+order['id'])
        self.assertEqual(content.json()['content'],'PRIVATE_TEST_CONTENT')
        self.assertEqual(content.json()['price_minor'],29900)
        self.assertEqual(content.headers['cache-control'],'no-store')
        self.assertEqual((await self.client.get('/api/v1/me/library/'+order['id']+'/download')).text,'PRIVATE_TEST_CONTENT')
    async def test_webhook_reverification_concurrency_and_refund(self):
        await self.register(self.client)
        order=(await self.post(self.client,'/api/v1/me/orders',{"prompt_id":"fixture-prompt"})).json()
        order_id=__import__('uuid').UUID(order['id']);bank_id=str(uuid4())
        async with self.factory() as db:
            db.add(Payment(order_id=order_id,bank_order_id=bank_id,status='pending'));await db.commit()
        payload={"mdOrder":bank_id,"orderNumber":order_id.hex,"operation":"deposited","status":1}
        result={"orderId":bank_id,"orderNumber":order_id.hex,"amount":29900,"currency":"643","orderStatus":2,"actionCode":0,"errorCode":"0"}
        settings=MagicMock();settings.sber_webhook_enabled=True
        with patch('app.payments.webhook.get_settings',return_value=settings),patch('app.payments.webhook.enabled',return_value=True),patch('app.payments.confirmation.call',new=AsyncMock(return_value={**result,'amount':1})):
            response=await self.client.post('/api/v1/payments/sber/webhook',json=payload)
            self.assertEqual(response.status_code,409)
            self.assertEqual((await self.client.get('/api/v1/me/library')).json(),[])
        with patch('app.payments.webhook.get_settings',return_value=settings),patch('app.payments.webhook.enabled',return_value=True),patch('app.payments.confirmation.call',new=AsyncMock(return_value=result)) as bank:
            responses=await asyncio.gather(*[self.client.post('/api/v1/payments/sber/webhook',json=payload) for _ in range(3)])
            self.assertTrue(all(r.status_code==200 for r in responses),[r.text for r in responses])
            self.assertEqual((await self.client.get('/api/v1/me/library/'+order['id'])).status_code,200)
            async with self.factory() as db:
                self.assertEqual(await db.scalar(select(func.count()).select_from(AuditLog).where(AuditLog.action=='order.sandbox_payment_confirmed')),1)
            bank.return_value={**result,'orderStatus':4}
            self.assertEqual((await self.client.post('/api/v1/payments/sber/webhook',json=payload)).status_code,200)
            self.assertEqual((await self.client.get('/api/v1/me/library/'+order['id'])).status_code,404)
            bank.side_effect=httpx.TimeoutException('fixture timeout')
        with patch('app.payments.webhook.get_settings',return_value=settings),patch('app.payments.webhook.enabled',return_value=True),patch('app.payments.confirmation.call',new=AsyncMock()) as bank:
            unknown={**payload,'mdOrder':str(uuid4())}
            self.assertEqual((await self.client.post('/api/v1/payments/sber/webhook',json=unknown)).status_code,200)
            bank.assert_not_awaited()

    async def manual_recipient(self):
        from cryptography.fernet import Fernet
        from pydantic import SecretStr
        from types import SimpleNamespace
        from app.payments.recipient import PaymentRecipient
        key = Fernet.generate_key()
        async with self.factory() as db:
            db.add(PaymentRecipient(id=1, recipient_name='Fixture Recipient', bank_name='Fixture Bank',
                encrypted_card=Fernet(key).encrypt(b'4242424242424242').decode(), card_last4='4242', revision=1))
            await db.commit()
        return SimpleNamespace(payment_details_encryption_key=SecretStr(key.decode()))

    async def test_manual_payment_snapshot_queue_and_concurrent_confirmation(self):
        from cryptography.fernet import Fernet
        from app.payments.recipient import PaymentRecipient
        from app.payments.manual_models import ManualPayment
        settings = await self.manual_recipient()
        await self.register(self.client)
        order = (await self.post(self.client, '/api/v1/me/orders', {'prompt_id': 'fixture-prompt'})).json()
        path = '/api/v1/me/orders/' + order['id'] + '/manual-payment'
        admin = await self.admin()
        try:
            self.assertEqual((await admin.get('/api/v1/admin/orders/pending-payments')).json()['total'], 0)
            with patch('app.payments.manual.get_settings', return_value=settings):
                results = await asyncio.gather(*[self.post(self.client, path, {}) for _ in range(3)])
                self.assertTrue(all(r.status_code == 200 for r in results), [r.text for r in results])
                self.assertEqual(results[0].json()['status'], 'awaiting_confirmation')
                self.assertNotIn('4242424242424242', results[0].text)
                details = await self.client.get(path)
                self.assertEqual(details.headers['cache-control'], 'no-store')
                self.assertEqual(details.json()['recipient']['card_number'], '4242424242424242')
                async with self.factory() as db:
                    recipient = await db.get(PaymentRecipient, 1)
                    recipient.recipient_name = 'New Recipient'
                    recipient.encrypted_card = Fernet(settings.payment_details_encryption_key.get_secret_value().encode()).encrypt(b'5555555555554444').decode()
                    recipient.card_last4 = '4444'; recipient.revision = 2
                    prompt = await db.get(Prompt, 'fixture-prompt'); prompt.price_minor = 99900
                    await db.commit()
                self.assertEqual((await self.client.get(path)).json()['recipient']['recipient_name'], 'Fixture Recipient')
                self.assertEqual((await self.client.get(path)).json()['recipient']['card_number'], '4242424242424242')
            queue = await admin.get('/api/v1/admin/orders/pending-payments')
            self.assertEqual(queue.json()['total'], 1)
            self.assertEqual(queue.json()['items'][0]['price_minor'], 29900)
            self.assertEqual(queue.json()['items'][0]['customer_contact'], 'fixture@example.com')
            self.assertEqual(queue.json()['items'][0]['masked_card'], '•••• •••• •••• 4242')
            self.assertNotIn('4242424242424242', queue.text)
            self.assertEqual((await self.client.get('/api/v1/me/library/' + order['id'])).status_code, 404)
            confirm = '/api/v1/admin/orders/' + order['id'] + '/confirm-payment'
            responses = await asyncio.gather(*[self.post(admin, confirm, {}) for _ in range(3)])
            self.assertTrue(all(r.status_code == 200 for r in responses), [r.text for r in responses])
            self.assertEqual((await self.client.get(path + '/status')).json()['status'], 'paid')
            self.assertEqual((await admin.get('/api/v1/admin/orders/pending-payments')).json()['total'], 0)
            self.assertEqual((await self.client.get('/api/v1/me/library/' + order['id'])).json()['content'], 'PRIVATE_TEST_CONTENT')
            self.assertEqual((await self.client.get('/api/v1/me/library/' + order['id'] + '/download')).text, 'PRIVATE_TEST_CONTENT')
            self.assertEqual(len((await self.client.get('/api/v1/me/library')).json()), 1)
            async with self.factory() as db:
                self.assertEqual(await db.scalar(select(func.count()).select_from(ManualPayment)), 1)
                for action in ['order.manual_payment_requested', 'order.manual_payment_confirmed']:
                    self.assertEqual(await db.scalar(select(func.count()).select_from(AuditLog).where(AuditLog.action == action)), 1)
                saved = await db.get(ManualPayment, __import__('uuid').UUID(order['id']))
                self.assertIsNotNone(saved.confirmed_at)
                self.assertIsNotNone(saved.confirmed_by)
                self.assertNotIn('4242424242424242', saved.encrypted_card)
        finally:
            await admin.aclose()

    async def test_manual_payment_ownership_admin_csrf_and_tampering(self):
        settings = await self.manual_recipient()
        await self.register(self.client)
        order = (await self.post(self.client, '/api/v1/me/orders', {'prompt_id': 'fixture-prompt'})).json()
        path = '/api/v1/me/orders/' + order['id'] + '/manual-payment'
        confirm = '/api/v1/admin/orders/' + order['id'] + '/confirm-payment'
        admin = await self.admin()
        try:
            self.assertEqual((await self.client.post(path, json={})).status_code, 403)
            self.assertEqual((await self.post(self.client, path, {'price_minor': 1, 'status': 'paid'})).status_code, 422)
            self.assertEqual((await self.client.get('/api/v1/admin/orders/pending-payments')).status_code, 403)
            self.assertEqual((await self.post(self.client, confirm, {})).status_code, 403)
            self.assertEqual((await self.post(admin, confirm, {})).status_code, 409)
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url=ORIGIN) as other:
                await self.register(other, 'other@example.com')
                self.assertEqual((await other.get(path)).status_code, 404)
                self.assertEqual((await other.get(path + '/status')).status_code, 404)
                self.assertEqual((await self.post(other, path, {})).status_code, 404)
            with patch('app.payments.manual.get_settings', return_value=settings):
                self.assertEqual((await self.post(self.client, path, {})).status_code, 200)
            self.assertEqual((await admin.post(confirm, json={})).status_code, 403)
            self.assertEqual((await self.post(admin, confirm, {'price_minor': 1})).status_code, 422)
            self.assertEqual((await self.client.get(path + '/status')).json()['status'], 'awaiting_confirmation')
            self.assertEqual((await self.client.get('/api/v1/me/library/' + order['id'])).status_code, 404)
        finally:
            await admin.aclose()

    async def test_manual_payment_missing_recipient_and_sandbox_conflict(self):
        await self.register(self.client)
        order = (await self.post(self.client, '/api/v1/me/orders', {'prompt_id': 'fixture-prompt'})).json()
        path = '/api/v1/me/orders/' + order['id'] + '/manual-payment'
        self.assertEqual((await self.post(self.client, path, {})).status_code, 503)
        self.assertEqual((await self.client.get(path + '/status')).json()['status'], 'pending')
        await self.manual_recipient()
        async with self.factory() as db:
            db.add(Payment(order_id=__import__('uuid').UUID(order['id']), status='pending'))
            await db.commit()
        self.assertEqual((await self.post(self.client, path, {})).status_code, 409)
        self.assertEqual((await self.client.get(path + '/status')).json()['status'], 'pending')

class MailTests(unittest.TestCase):
    def test_smtp_uses_tls_and_never_plaintext_fallback(self):
        from app.auth.mail import send_smtp_message
        settings=MagicMock(smtp_host='smtp.example.invalid',smtp_port=465,smtp_security='ssl',smtp_username='fixture@example.com',smtp_from='fixture@example.com')
        settings.smtp_password.get_secret_value.return_value='fixture-secret'
        with patch('app.auth.mail.get_settings',return_value=settings),patch('app.auth.mail.smtplib.SMTP_SSL') as smtp:
            smtp.return_value.__enter__.return_value.send_message.return_value={}
            send_smtp_message('fixture-message',{'email':'recipient@example.com','subject':'Fixture','text':'Test','link':'https://example.com/#token=fixture'})
            self.assertIn('context',smtp.call_args.kwargs)
            smtp.return_value.__enter__.return_value.login.assert_called_once_with('fixture@example.com','fixture-secret')
        settings.smtp_security='starttls'
        with patch('app.auth.mail.get_settings',return_value=settings),patch('app.auth.mail.smtplib.SMTP') as smtp:
            smtp.return_value.__enter__.return_value.starttls.side_effect=RuntimeError('TLS failed')
            with self.assertRaises(RuntimeError):send_smtp_message('fixture',{'email':'recipient@example.com','subject':'Fixture','text':'Test'})
            smtp.return_value.__enter__.return_value.login.assert_not_called()
class ProxyIdentityTests(unittest.TestCase):
    def test_unsigned_identity_rejected_and_clients_have_separate_buckets(self):
        import hmac,hashlib
        from types import SimpleNamespace
        from pydantic import SecretStr
        from starlette.requests import Request
        from fastapi import HTTPException
        from app.auth.security import limit_attempts
        secret=secrets.token_urlsafe(32)
        settings=SimpleNamespace(auth_proxy_secret=SecretStr(secret),app_env="production")
        def request(identity,valid=True):
            signature=hmac.new(secret.encode(),("pm-client:"+identity).encode(),hashlib.sha256).hexdigest() if valid else "invalid"
            return Request({"type":"http","headers":[(b"x-pm-client",identity.encode()),(b"x-pm-proxy-signature",signature.encode())],"client":("proxy",1234)})
        _attempts.clear()
        with patch('app.auth.security.get_settings',return_value=settings):
            with self.assertRaises(HTTPException) as error:limit_attempts(request("a"*64,False))
            self.assertEqual(error.exception.status_code,403)
            for _ in range(60):limit_attempts(request("a"*64))
            with self.assertRaises(HTTPException) as error:limit_attempts(request("a"*64))
            self.assertEqual(error.exception.status_code,429)
            limit_attempts(request("b"*64))
        _attempts.clear()

if __name__=='__main__':unittest.main()
