import asyncio
from decimal import Decimal
from types import SimpleNamespace
from uuid import UUID, uuid4
from unittest.mock import AsyncMock, patch
from fastapi import HTTPException
from pydantic import SecretStr
import httpx
from sqlalchemy import func, select
from app.main import app
from app.admin.models import AuditLog
from app.payments.platega_models import PlategaPayment
from tests.test_security import ORIGIN, SecurityFixture


class PlategaTests(SecurityFixture):
    async def asyncSetUp(self):
        await super().asyncSetUp()
        self.settings = SimpleNamespace(platega_enabled=True, platega_merchant_id=uuid4(),
            platega_secret=SecretStr('fixture-platega-secret'), public_web_url=ORIGIN, app_env='test')
        for module in ['app.payments.platega', 'app.payments.platega_router']:
            item = patch(module + '.get_settings', return_value=self.settings)
            self.patches.append(item); item.start()
        await self.register(self.client)
        self.order = (await self.post(self.client, '/api/v1/me/orders', {'prompt_id': 'fixture-prompt'})).json()
        self.path = '/api/v1/me/orders/' + self.order['id'] + '/platega-payment'

    async def begin(self):
        transaction_id = uuid4()
        result = {'transactionId': str(transaction_id), 'merchantId': str(self.settings.platega_merchant_id),
                  'redirect': 'https://pay.platega.io/?id=' + str(transaction_id), 'status': 'PENDING'}
        with patch('app.payments.platega_router.call', new=AsyncMock(return_value=result)) as provider:
            response = await self.post(self.client, self.path, {})
            self.assertEqual(response.status_code, 200, response.text)
        async with self.factory() as db:
            payment = await db.scalar(select(PlategaPayment).where(PlategaPayment.transaction_id == transaction_id))
        return payment, provider

    def provider_result(self, payment, **overrides):
        return {'id': str(payment.transaction_id), 'mechantId': str(self.settings.platega_merchant_id),
                'status': 'CONFIRMED', 'paymentDetails': {'amount': Decimal('299.00'), 'currency': 'RUB'},
                'payload': str(payment.id), 'amountUsdt': Decimal('3.1'), 'comissionUsdt': Decimal('0.1'), **overrides}

    async def notify(self, payment, *, secret='fixture-platega-secret', payload=False):
        return await self.client.post('/api/v1/payments/platega/webhook',
            json={'id': str(payment.transaction_id), 'status': 'CONFIRMED', **({'payload': str(payment.id)} if payload else {})},
            headers={'X-MerchantId': str(self.settings.platega_merchant_id), 'X-Secret': secret})

    async def test_creation_reuses_checkout_and_enforces_server_price_csrf_and_owner(self):
        self.assertEqual((await self.client.post(self.path, json={})).status_code, 403)
        self.assertEqual((await self.post(self.client, self.path, {'amount': 1, 'status': 'paid'})).status_code, 422)
        payment, provider = await self.begin()
        payload = provider.call_args.args[2]
        self.assertEqual(payload['paymentDetails'], {'amount': 299, 'currency': 'RUB'})
        self.assertEqual(payload['paymentMethod'], 2)
        self.assertEqual(payload['payload'], str(payment.id))
        self.assertIn('userId', payload['metadata'])
        with patch('app.payments.platega_router.call', new=AsyncMock()) as provider:
            responses = await asyncio.gather(*[self.post(self.client, self.path, {}) for _ in range(3)])
            self.assertTrue(all(r.status_code == 200 for r in responses))
            self.assertTrue(all(r.json()['checkout_url'] == payment.checkout_url for r in responses))
            provider.assert_not_awaited()
        self.assertEqual((await self.client.get('/api/v1/me/library/' + self.order['id'])).status_code, 404)
        self.assertEqual((await self.client.get(self.path)).headers['cache-control'], 'no-store')
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url=ORIGIN) as other:
            await self.register(other, 'other@example.com')
            self.assertEqual((await other.get(self.path)).status_code, 404)
            self.assertEqual((await self.post(other, self.path, {})).status_code, 404)
            self.assertEqual((await self.post(other, self.path + '/check', {})).status_code, 404)
        async with self.factory() as db:
            self.assertEqual(await db.scalar(select(func.count()).select_from(PlategaPayment)), 1)

    async def test_callback_authentication_reverification_concurrency_and_chargeback(self):
        payment, _ = await self.begin()
        with patch('app.payments.platega.call', new=AsyncMock()) as provider:
            self.assertEqual((await self.notify(payment, secret='wrong-secret')).status_code, 403)
            provider.assert_not_awaited()
        for override in [
            {'paymentDetails': {'amount': '1', 'currency': 'RUB'}}, {'mechantId': str(uuid4())},
            {'id': str(uuid4())}, {'payload': str(uuid4())}, {'paymentDetails': {'amount': '299', 'currency': 'USD'}},
        ]:
            with patch('app.payments.platega.call', new=AsyncMock(return_value=self.provider_result(payment, **override))):
                self.assertEqual((await self.notify(payment)).status_code, 409)
                self.assertEqual((await self.client.get('/api/v1/me/library/' + self.order['id'])).status_code, 404)
        with patch('app.payments.platega.call', new=AsyncMock(return_value=self.provider_result(payment))) as provider:
            responses = await asyncio.gather(*[self.notify(payment) for _ in range(3)])
            self.assertTrue(all(r.status_code == 200 for r in responses), [r.text for r in responses])
            self.assertEqual((await self.client.get('/api/v1/me/library/' + self.order['id'])).json()['content'], 'PRIVATE_TEST_CONTENT')
            self.assertEqual((await self.client.get(self.path)).json()['status'], 'paid')
            provider.return_value = self.provider_result(payment, status='CHARGEBACKED')
            self.assertEqual((await self.notify(payment)).status_code, 200)
            self.assertEqual((await self.client.get('/api/v1/me/library/' + self.order['id'])).status_code, 404)
            provider.return_value = self.provider_result(payment)
            self.assertEqual((await self.notify(payment)).status_code, 200)
            self.assertEqual((await self.client.get('/api/v1/me/library/' + self.order['id'])).status_code, 404)
        async with self.factory() as db:
            for action in ['order.platega_payment_confirmed', 'order.platega_access_revoked']:
                self.assertEqual(await db.scalar(select(func.count()).select_from(AuditLog).where(AuditLog.action == action)), 1)

    async def test_timeout_keeps_intent_and_callback_can_recover_it(self):
        with patch('app.payments.platega_router.call', new=AsyncMock(side_effect=HTTPException(503, 'Fixture timeout'))) as provider:
            self.assertEqual((await self.post(self.client, self.path, {})).status_code, 503)
            self.assertEqual((await self.post(self.client, self.path, {})).status_code, 409)
            self.assertEqual(provider.await_count, 1)
        async with self.factory() as db:
            payment = await db.scalar(select(PlategaPayment))
            self.assertEqual(payment.status, 'UNKNOWN')
            self.assertIsNone(payment.transaction_id)
        payment.transaction_id = uuid4()
        with patch('app.payments.platega.call', new=AsyncMock(return_value=self.provider_result(payment))):
            self.assertEqual((await self.notify(payment, payload=True)).status_code, 200)
            self.assertEqual((await self.client.get(self.path)).json()['status'], 'paid')

    async def test_manual_waiting_order_can_switch_to_platega_without_manual_confirmation(self):
        from app.orders.models import Order
        from app.payments.manual_models import ManualPayment
        order_id = UUID(self.order['id'])
        async with self.factory() as db:
            order = await db.get(Order, order_id)
            order.status = 'awaiting_confirmation'
            db.add(ManualPayment(order_id=order_id, recipient_name='Previous recipient', bank_name='Fixture bank',
                                 encrypted_card='previous-encrypted-card', card_last4='4242', recipient_revision=1))
            await db.commit()
        self.settings.platega_enabled = False
        self.assertEqual((await self.post(self.client, self.path, {})).status_code, 503)
        self.assertEqual((await self.client.get(self.path)).json()['status'], 'awaiting_confirmation')
        async with self.factory() as db:
            self.assertEqual(await db.scalar(select(func.count()).select_from(PlategaPayment)), 0)
        self.settings.platega_enabled = True
        payment, _ = await self.begin()
        self.assertEqual((await self.client.get(self.path)).json()['status'], 'pending')
        self.assertIsNone((await self.client.get('/api/v1/me/orders/' + self.order['id'] + '/manual-payment')).json()['recipient'])
        admin = await self.admin()
        try:
            self.assertEqual((await admin.get('/api/v1/admin/orders/pending-payments')).json()['total'], 0)
            response = await self.post(admin, '/api/v1/admin/orders/' + self.order['id'] + '/confirm-payment', {})
            self.assertEqual(response.status_code, 409)
        finally:
            await admin.aclose()
        self.assertEqual((await self.client.get('/api/v1/me/library/' + self.order['id'])).status_code, 404)
        with patch('app.payments.platega.call', new=AsyncMock(return_value=self.provider_result(payment))):
            self.assertEqual((await self.notify(payment)).status_code, 200)
        self.assertEqual((await self.client.get('/api/v1/me/library/' + self.order['id'])).status_code, 200)
        async with self.factory() as db:
            manual = await db.get(ManualPayment, order_id)
            self.assertEqual(manual.encrypted_card, 'previous-encrypted-card')
            self.assertIsNone(manual.confirmed_at)
            self.assertEqual(await db.scalar(select(func.count()).select_from(AuditLog).where(AuditLog.action == 'order.payment_provider_changed')), 1)

    async def test_expired_checkout_can_retry_without_overwriting_history(self):
        payment, _ = await self.begin()
        with patch('app.payments.platega.call', new=AsyncMock(return_value=self.provider_result(payment, status='EXPIRED'))):
            response = await self.post(self.client, self.path + '/check', {})
            self.assertEqual(response.status_code, 200, response.text)
            self.assertEqual(response.json()['provider_status'], 'EXPIRED')
        second, _ = await self.begin()
        self.assertNotEqual(second.id, payment.id)
        async with self.factory() as db:
            self.assertEqual(await db.scalar(select(func.count()).select_from(PlategaPayment)), 2)
            self.assertEqual((await db.get(PlategaPayment, payment.id)).status, 'EXPIRED')

    async def test_configuration_redirect_validation_and_cross_provider_conflicts(self):
        from app.payments.platega import safe_checkout_url, public_url_ready
        for url in ['http://localhost:3107', 'https://localhost.', 'https://127.0.0.1', 'https://[::1]', 'https://10.0.0.1', 'https://shop.local']:
            self.settings.public_web_url = url
            self.assertFalse(public_url_ready(), url)
        self.settings.public_web_url = 'https://shop.example.com'
        self.assertTrue(public_url_ready())
        self.settings.public_web_url = ORIGIN
        for url in ['http://pay.platega.io', 'https://pay.platega.io.evil.example', 'https://pay.platega.io@evil.example', 'https://pay.platega.io:444', 'javascript:alert(1)', 'https://pay.platega.io\\@evil.example', 'https://pay.platega.io:invalid']:
            self.assertIsNone(safe_checkout_url(url), url)
        self.settings.platega_enabled = False
        with patch('app.payments.platega_router.call', new=AsyncMock()) as provider:
            self.assertEqual((await self.post(self.client, self.path, {})).status_code, 503)
            provider.assert_not_awaited()
        self.settings.platega_enabled = True
        await self.begin()
        self.assertEqual((await self.post(self.client, '/api/v1/me/orders/' + self.order['id'] + '/manual-payment', {})).status_code, 409)
        self.assertEqual((await self.client.get('/api/v1/admin/payments/platega')).status_code, 403)
        admin = await self.admin()
        try:
            with patch('app.orders.router.test_access_enabled', return_value=True):
                self.assertEqual((await self.post(admin, '/api/v1/admin/orders/' + self.order['id'] + '/test-access', {})).status_code, 409)
            response = await admin.get('/api/v1/admin/payments/platega')
            self.assertEqual(response.status_code, 200)
            self.assertNotIn('fixture-platega-secret', response.text)
            self.assertEqual((await self.post(admin, '/api/v1/admin/orders/' + self.order['id'] + '/confirm-payment', {})).status_code, 409)
        finally:
            await admin.aclose()
