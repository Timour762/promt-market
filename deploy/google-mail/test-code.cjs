const assert = require('node:assert/strict');
const { createHmac } = require('node:crypto');
const { readFileSync } = require('node:fs');
const { join } = require('node:path');
const { test } = require('node:test');
const { runInNewContext } = require('node:vm');

const code = readFileSync(join(__dirname, 'Code.gs'), 'utf8');
const fixtureSecret = 'fixture-google-mail-secret-longer-than-32-characters';
const id = '95363968-0869-43ce-9a85-60fe4660c79f';

function fixture(options = {}) {
  const properties = new Map([['GOOGLE_MAIL_SECRET', fixtureSecret]]);
  const sent = [];
  let held = false;
  const context = {
    ContentService: {
      MimeType: { JSON: 'application/json' },
      createTextOutput(text) { return { text, setMimeType() { return this; } }; },
    },
    Utilities: {
      Charset: { UTF_8: 'UTF-8' },
      computeHmacSha256Signature(text, secret) { return [...createHmac('sha256', secret).update(text, 'utf8').digest()]; },
    },
    PropertiesService: {
      getScriptProperties() {
        return {
          getProperty: key => properties.get(key) ?? null,
          setProperty: (key, value) => properties.set(key, value),
          deleteProperty: key => properties.delete(key),
          getProperties: () => Object.fromEntries(properties),
        };
      },
    },
    LockService: {
      getScriptLock() { return { tryLock() { held = options.locked !== true; return held; }, hasLock: () => held, releaseLock() { held = false; } }; },
    },
    MailApp: {
      getRemainingDailyQuota: () => options.quota ?? 100,
      sendEmail(value) {
        if (options.fail) throw new Error('provider-private-email-and-link');
        sent.push(JSON.parse(JSON.stringify(value)));
      },
    },
  };
  runInNewContext(code, context, { filename: 'Code.gs' });
  function request(overrides = {}, rawChanges = {}) {
    const payload = JSON.stringify({ id, issued_at: Math.floor(Date.now() / 1000), to: 'buyer@example.com', subject: 'Подтверждение email', text: 'Сервисное письмо', ...overrides });
    const body = { payload, signature: createHmac('sha256', fixtureSecret).update(payload, 'utf8').digest('hex'), ...rawChanges };
    const contents = JSON.stringify(body);
    return { postData: { type: 'application/json', contents }, contentLength: Buffer.byteLength(contents) };
  }
  const call = event => JSON.parse(context.doPost(event).text);
  return { call, request, sent, properties, context, held: () => held };
}

test('signed Unicode message is accepted and no personal content is persisted', () => {
  const f = fixture();
  assert.deepEqual(f.call(f.request()), { ok: true, id });
  assert.equal(f.sent.length, 1);
  assert.equal(f.sent[0].subject, 'Подтверждение email');
  assert.equal(f.sent[0].name, 'ПромтМаркет');
  assert.deepEqual([...f.properties.keys()].sort(), ['GOOGLE_MAIL_SECRET', 'sent_' + id].sort());
  assert.equal(f.held(), false);
});

test('repeated authenticated job is acknowledged without sending another email', () => {
  const f = fixture();
  const event = f.request();
  f.call(event);
  assert.deepEqual(f.call(event), { ok: true, id });
  assert.equal(f.sent.length, 1);
});

test('missing key, invalid signatures and tampered payloads cannot send mail', () => {
  const f = fixture();
  assert.equal(f.call(f.request({}, { signature: '0'.repeat(64) })).ok, false);
  const event = f.request();
  const body = JSON.parse(event.postData.contents);
  body.payload = body.payload.replace('buyer@example.com', 'other@example.com');
  event.postData.contents = JSON.stringify(body);
  assert.equal(f.call(event).ok, false);
  f.properties.delete('GOOGLE_MAIL_SECRET');
  assert.equal(f.call(f.request()).ok, false);
  assert.equal(f.sent.length, 0);
});

test('expired and future-dated requests cannot send mail', () => {
  const f = fixture();
  for (const issued_at of [0, Math.floor(Date.now() / 1000) + 900]) {
    assert.equal(f.call(f.request({ issued_at })).ok, false);
  }
  assert.equal(f.sent.length, 0);
});

test('multiple recipients, header injection, bad job types and oversized input fail closed', () => {
  const f = fixture();
  for (const overrides of [{ to: 'one@example.com,two@example.com' }, { to: 'one@example.com;two@example.com' }, { subject: 'Subject\r\nBcc: other@example.com' }, { text: 'x'.repeat(8001) }, { op: 'unknown' }, { id: 'invalid' }, { issued_at: '123' }]) {
    assert.equal(f.call(f.request(overrides)).ok, false);
  }
  const large = f.request();
  large.contentLength = 16385;
  assert.equal(f.call(large).ok, false);
  assert.equal(f.sent.length, 0);
});

test('quota and lock contention keep a job unsent and unacknowledged', () => {
  for (const options of [{ quota: 0 }, { locked: true }]) {
    const f = fixture(options);
    assert.equal(f.call(f.request()).ok, false);
    assert.equal(f.sent.length, 0);
    assert.equal(f.properties.has('sent_' + id), false);
  }
});

test('mail provider errors are sanitized and lock is released', () => {
  const f = fixture({ fail: true });
  const result = f.call(f.request());
  assert.deepEqual(result, { ok: false, error: 'delivery_failed' });
  assert.equal(JSON.stringify(result).includes('private'), false);
  assert.equal(f.held(), false);
});

test('authenticated connectivity probe and authorization do not send messages', () => {
  const f = fixture();
  assert.deepEqual(f.call(f.request({ op: 'check' })), { ok: true, id, remainingDailyQuota: 100 });
  assert.equal(f.context.authorizeMail(), 100);
  assert.equal(f.sent.length, 0);
});

test('unauthenticated GET and malformed JSON do not reveal account or quota', () => {
  const f = fixture();
  assert.deepEqual(JSON.parse(f.context.doGet().text), { ok: false, error: 'post_required' });
  assert.equal(f.call({ postData: { contents: '{', type: 'application/json' } }).ok, false);
  assert.equal(f.call({}).ok, false);
  assert.equal(f.sent.length, 0);
});

test('cleanup removes old job markers while keeping the shared secret', () => {
  const f = fixture();
  const oldKey = 'sent_00000000-0000-0000-0000-000000000000';
  f.properties.set(oldKey, '1');
  f.call(f.request());
  assert.equal(f.properties.has(oldKey), false);
  assert.equal(f.properties.get('GOOGLE_MAIL_SECRET'), fixtureSecret);
});
