/**
 * PromtMarket transactional mail endpoint. Deploy as Me / Anyone.
 * Set GOOGLE_MAIL_SECRET in Script Properties; never place it in this source.
 * MailApp sends as this script's owner and does not read the owner's inbox.
 */

const MAX_REQUEST_BYTES = 16384;
const CLOCK_SKEW_SECONDS = 300;
const DEDUP_SECONDS = 7 * 24 * 60 * 60;

function jsonReply(value) {
  return ContentService.createTextOutput(JSON.stringify(value))
    .setMimeType(ContentService.MimeType.JSON);
}

function equalSignature(left, right) {
  if (typeof left !== 'string' || !/^[0-9a-f]{64}$/.test(left)) return false;
  let difference = 0;
  for (let i = 0; i < 64; i++) {
    difference |= left.charCodeAt(i) ^ right.charCodeAt(i);
  }
  return difference === 0;
}

function signatureFor(payload, secret) {
  const bytes = Utilities.computeHmacSha256Signature(payload, secret, Utilities.Charset.UTF_8);
  return bytes.map(function (value) {
    return ((value + 256) % 256).toString(16).padStart(2, '0');
  }).join('');
}

function validJob(job, now) {
  return job && typeof job === 'object' && !Array.isArray(job)
    && typeof job.id === 'string'
    && /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/.test(job.id)
    && Number.isInteger(job.issued_at)
    && Math.abs(now - job.issued_at) <= CLOCK_SKEW_SECONDS;
}

function validMessage(job) {
  return typeof job.to === 'string' && job.to.length <= 254
    && /^[^@\s,;<>]+@[^@\s,;<>]+\.[^@\s,;<>]+$/.test(job.to)
    && typeof job.subject === 'string' && job.subject.trim().length > 0
    && job.subject.length <= 200 && !/[\r\n]/.test(job.subject)
    && typeof job.text === 'string' && job.text.length > 0 && job.text.length <= 8000;
}

function doGet() {
  return jsonReply({ok: false, error: 'post_required'});
}

function doPost(event) {
  let lock;
  try {
    if (!event || !event.postData || typeof event.postData.contents !== 'string'
        || event.postData.contents.length > MAX_REQUEST_BYTES
        || (event.contentLength > MAX_REQUEST_BYTES)
        || !/^application\/json(?:\s*;|$)/i.test(event.postData.type || '')) {
      return jsonReply({ok: false, error: 'invalid_request'});
    }
    const body = JSON.parse(event.postData.contents);
    if (!body || typeof body.payload !== 'string' || body.payload.length > MAX_REQUEST_BYTES) {
      return jsonReply({ok: false, error: 'invalid_request'});
    }
    const properties = PropertiesService.getScriptProperties();
    const secret = properties.getProperty('GOOGLE_MAIL_SECRET');
    if (!secret || secret.length < 32
        || !equalSignature(body.signature, signatureFor(body.payload, secret))) {
      return jsonReply({ok: false, error: 'unauthorized'});
    }
    const job = JSON.parse(body.payload);
    const now = Math.floor(Date.now() / 1000);
    if (!validJob(job, now)) return jsonReply({ok: false, error: 'invalid_request'});
    if (job.op === 'check') {
      return jsonReply({ok: true, id: job.id, remainingDailyQuota: MailApp.getRemainingDailyQuota()});
    }
    if ((job.op !== undefined && job.op !== 'send') || !validMessage(job)) {
      return jsonReply({ok: false, error: 'invalid_request'});
    }
    lock = LockService.getScriptLock();
    if (!lock.tryLock(5000)) return jsonReply({ok: false, error: 'busy'});

    const sentKey = 'sent_' + job.id;
    if (properties.getProperty(sentKey)) return jsonReply({ok: true, id: job.id});
    if (MailApp.getRemainingDailyQuota() < 1) return jsonReply({ok: false, error: 'quota'});

    // Only completed job ids/timestamps are stored: never recipients, text or links.
    const saved = properties.getProperties();
    Object.keys(saved).forEach(function (key) {
      if (key.indexOf('sent_') === 0 && Number(saved[key]) < now - DEDUP_SECONDS) {
        properties.deleteProperty(key);
      }
    });
    MailApp.sendEmail({to: job.to, subject: job.subject, body: job.text, name: 'ПромтМаркет'});
    properties.setProperty(sentKey, String(now));
    return jsonReply({ok: true, id: job.id});
  } catch (error) {
    // Provider exceptions can contain email addresses: do not print or return them.
    return jsonReply({ok: false, error: 'delivery_failed'});
  } finally {
    if (lock && lock.hasLock()) lock.releaseLock();
  }
}

/** Run once in the editor to grant send-mail permission. Sends no message. */
function authorizeMail() {
  return MailApp.getRemainingDailyQuota();
}
