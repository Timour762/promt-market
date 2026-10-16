from functools import lru_cache
from pathlib import Path
from typing import Literal
from cryptography.fernet import Fernet
from pydantic import field_validator, model_validator, EmailStr
from pydantic import SecretStr, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    sber_sandbox_enabled: bool = False
    sber_webhook_enabled: bool = False
    sber_username: str | None = None
    sber_password: SecretStr | None = None
    local_test_access_enabled: bool = False
    app_name: str = "PromtMarket API"
    database_url: str = "postgresql+asyncpg://promt:local_only@localhost:5438/promt_market"
    csrf_secret: SecretStr = Field(min_length=32)
    mail_encryption_key: SecretStr
    public_web_url: str = "http://localhost:3107"
    app_env: Literal["local", "production", "test"] = "local"
    auth_proxy_secret: SecretStr | None = Field(default=None,min_length=32)
    mail_delivery: Literal["local", "smtp"] = "local"
    smtp_host: str = "smtp.mail.ru"
    smtp_port: int = Field(default=465, ge=1, le=65535)
    smtp_security: Literal["ssl", "starttls"] = "ssl"
    smtp_username: str | None = None
    smtp_password: SecretStr | None = None
    smtp_from: EmailStr = "promtmarket@mail.ru"
    legal_ready: bool = False

    @model_validator(mode="after")
    def validate_runtime(self):
        if self.mail_delivery == "smtp" and (not self.smtp_username or not self.smtp_password or not self.smtp_password.get_secret_value()):
            raise ValueError("SMTP mode requires SMTP_USERNAME and SMTP_PASSWORD")
        if self.app_env == "production":
            if not self.auth_proxy_secret:
                raise ValueError("Production requires an authentication proxy secret")
            if not self.cookie_secure or not self.public_web_url.startswith("https://"):
                raise ValueError("Production requires HTTPS and secure cookies")
            if self.local_test_access_enabled or self.sber_sandbox_enabled or self.sber_webhook_enabled:
                raise ValueError("Sandbox and educational access must be disabled in production")
            if self.mail_delivery != "smtp" or not self.legal_ready:
                raise ValueError("Production requires configured mail and finalized legal documents")
            if any(not origin.startswith("https://") for origin in self.allowed_origins):
                raise ValueError("Production origins must use HTTPS")
        return self
    local_mail_dir: Path = Path(__file__).resolve().parents[3] / ".local" / "mail"
    cookie_secure: bool = False
    session_days: int = Field(default=7, ge=1, le=30)
    allowed_origins: list[str] = ["http://localhost:3107", "http://127.0.0.1:3107"]
    @field_validator("mail_encryption_key")
    @classmethod
    def validate_mail_key(cls, value: SecretStr):
        Fernet(value.get_secret_value().encode())
        return value

    @field_validator("public_web_url")
    @classmethod
    def validate_web_url(cls, value: str):
        from urllib.parse import urlsplit
        parts = urlsplit(value)
        if parts.scheme not in ("http", "https") or not parts.netloc or parts.query or parts.fragment or parts.username or parts.password or parts.path not in ("", "/"):
            raise ValueError("PUBLIC_WEB_URL must be a trusted origin without path or credentials")
        return value.rstrip("/")

    model_config = SettingsConfigDict(env_file=".env", extra="ignore", hide_input_in_errors=True)

@lru_cache
def get_settings() -> Settings:
    return Settings()
