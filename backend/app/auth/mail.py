import json
import logging
import smtplib
import ssl
from email.message import EmailMessage
from email.utils import format_datetime
from datetime import datetime, timezone
from html import escape
from pathlib import Path
from cryptography.fernet import Fernet
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.concurrency import run_in_threadpool
from app.auth.recovery_models import EmailOutbox
from app.core.config import get_settings
from app.db.session import SessionFactory

logger = logging.getLogger(__name__)

def cipher() -> Fernet:
    return Fernet(get_settings().mail_encryption_key.get_secret_value().encode())

def enqueue_mail(db: AsyncSession, email: str, subject: str, text: str, link: str | None = None):
    payload = json.dumps({"email": email, "subject": subject, "text": text, "link": link}, ensure_ascii=False)
    db.add(EmailOutbox(encrypted_payload=cipher().encrypt(payload.encode()).decode()))

def save_local_message(message_id: str, payload: dict):
    folder = get_settings().local_mail_dir
    folder.mkdir(parents=True, exist_ok=True)
    target = folder / f"{message_id}.html"
    if target.exists():
        return  # Same outbox event is never duplicated after a restart.
    link = payload.get("link")
    action = f'<p><a href="{escape(link, quote=True)}">Открыть ссылку</a></p>' if link else ""
    page = f'<!doctype html><html lang="ru"><meta charset="utf-8"><meta name="referrer" content="no-referrer"><title>{escape(payload["subject"])}</title><body style="font-family:Segoe UI,sans-serif;max-width:640px;margin:50px auto;padding:24px;line-height:1.7"><p>ЛОКАЛЬНОЕ ПИСЬМО. НАРУЖУ НЕ ОТПРАВЛЕНО.</p><p>Кому: {escape(payload["email"])}</p><h1>{escape(payload["subject"])}</h1><p>{escape(payload["text"])}</p>{action}<p>Если вы не запрашивали это действие, проигнорируйте письмо.</p></body></html>'
    temporary = target.with_suffix(".tmp")
    temporary.write_text(page, encoding="utf-8")
    temporary.replace(target)

def send_smtp_message(message_id: str, payload: dict):
    settings = get_settings()
    message = EmailMessage()
    message["From"] = f"ПромтМаркет <{settings.smtp_from}>"
    message["To"] = payload["email"]
    message["Subject"] = payload["subject"]
    message["Date"] = format_datetime(datetime.now(timezone.utc))
    message["Message-ID"] = f"<{message_id}@{str(settings.smtp_from).split('@')[1]}>"
    text = payload["text"]
    if payload.get("link"):
        text += "\n\n" + payload["link"]
    text += "\n\nЕсли вы не запрашивали это действие, проигнорируйте письмо."
    message.set_content(text)
    context = ssl.create_default_context()
    smtp_type = smtplib.SMTP_SSL if settings.smtp_security == "ssl" else smtplib.SMTP
    kwargs = {"timeout": 15}
    if settings.smtp_security == "ssl":
        kwargs["context"] = context
    with smtp_type(settings.smtp_host, settings.smtp_port, **kwargs) as client:
        if settings.smtp_security == "starttls":
            client.ehlo()
            client.starttls(context=context)
            client.ehlo()
        client.login(settings.smtp_username, settings.smtp_password.get_secret_value())
        refused = client.send_message(message)
        if refused:
            raise RuntimeError("SMTP recipient rejected")

async def deliver_mail():
    # Runs after committed requests or explicitly via CLI. No polling/timers.
    try:
        async with SessionFactory() as db, db.begin():
            messages = (await db.scalars(select(EmailOutbox).where(EmailOutbox.delivered_at.is_(None), EmailOutbox.encrypted_payload.is_not(None), EmailOutbox.attempts < 5).order_by(EmailOutbox.created_at).limit(25).with_for_update(skip_locked=True))).all()
            for message in messages:
                message.attempts += 1
                try:
                    payload = json.loads(cipher().decrypt(message.encrypted_payload.encode()))
                    sender = send_smtp_message if get_settings().mail_delivery == "smtp" else save_local_message
                    await run_in_threadpool(sender, str(message.id), payload)
                    message.delivered_at = datetime.now(timezone.utc)
                    message.last_error = None
                    message.encrypted_payload = None
                except Exception:
                    # Never log the encrypted payload, recipient or link.
                    message.last_error = "mail_delivery_failed"
                    logger.warning("Mail delivery failed; message remains queued")
    except Exception:
        logger.warning("Mail outbox unavailable; retry with app.deliver_mail")

# Keep compatibility for existing imports and the local delivery CLI.
deliver_local_mail = deliver_mail
