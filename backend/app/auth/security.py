import hashlib
import hmac
import secrets
import time
from collections import OrderedDict
from argon2 import PasswordHasher
from argon2.exceptions import VerificationError, InvalidHashError
from fastapi import HTTPException, Request
from app.core.config import get_settings

SESSION_COOKIE = "pm_session"
CSRF_COOKIE = "pm_csrf"
password_hasher = PasswordHasher(time_cost=3, memory_cost=65536, parallelism=1)
DUMMY_HASH = password_hasher.hash(secrets.token_urlsafe(32))
# Single-process local limiter. Replace with shared storage before multi-worker release.
_attempts: OrderedDict[str, tuple[int, float]] = OrderedDict()

def token_hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()

def verify_password(encoded: str, password: str) -> bool:
    try:
        return password_hasher.verify(encoded, password)
    except (VerificationError, InvalidHashError):
        return False

def new_csrf_token() -> str:
    message = f"{int(time.time())}.{secrets.token_urlsafe(32)}"
    signature = hmac.new(get_settings().csrf_secret.get_secret_value().encode(), message.encode(), hashlib.sha256).hexdigest()
    return f"{message}.{signature}"

def require_csrf(request: Request):
    if request.headers.get("origin") not in get_settings().allowed_origins:
        raise HTTPException(status_code=403, detail="Недопустимый источник запроса")
    cookie = request.cookies.get(CSRF_COOKIE, "")
    header = request.headers.get("x-csrf-token", "")
    if not cookie or len(cookie) > 256 or not hmac.compare_digest(cookie, header):
        raise HTTPException(status_code=403, detail="Обновите страницу и повторите действие")
    try:
        timestamp, nonce, signature = cookie.split(".")
        age = time.time() - int(timestamp)
    except (ValueError, TypeError):
        raise HTTPException(status_code=403, detail="Недействительный токен запроса")
    message = f"{timestamp}.{nonce}"
    expected = hmac.new(get_settings().csrf_secret.get_secret_value().encode(), message.encode(), hashlib.sha256).hexdigest()
    if not 0 <= age <= 3600 or not hmac.compare_digest(signature, expected):
        raise HTTPException(status_code=403, detail="Обновите страницу и повторите действие")

def limit_attempts(request: Request, email: str = ""):
    now = time.monotonic()
    host = request.client.host if request.client else "unknown"
    settings = get_settings()
    if settings.auth_proxy_secret:
        identity = request.headers.get("x-pm-client", "")
        signature = request.headers.get("x-pm-proxy-signature", "")
        expected = hmac.new(settings.auth_proxy_secret.get_secret_value().encode(), ("pm-client:" + identity).encode(), hashlib.sha256).hexdigest()
        valid = len(identity) == 64 and all(char in "0123456789abcdef" for char in identity) and hmac.compare_digest(expected, signature)
        if not valid:
            raise HTTPException(status_code=403, detail="Недоверенный источник запроса")
        host = identity
    elif settings.app_env == "production":
        raise HTTPException(status_code=503, detail="Ограничение запросов не настроено")
    # One API process in compose. Multiple processes require a shared store.
    keys = [("host:" + host, 60)]
    if email:
        keys.append(("email:" + token_hash(email), 10))
    for key, limit in keys:
        count, since = _attempts.get(key, (0, now))
        if now - since >= 900:
            count, since = 0, now
        if count >= limit:
            raise HTTPException(status_code=429, detail="Слишком много попыток. Подождите 15 минут.", headers={"Retry-After": "900"})
        _attempts[key] = (count + 1, since)
        _attempts.move_to_end(key)
    while len(_attempts) > 10000:
        _attempts.popitem(last=False)
