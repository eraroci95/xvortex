from functools import lru_cache

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Fails closed: an unset ENVIRONMENT means production (Secure cookies, API docs off).
    # Local development sets ENVIRONMENT=development in backend/.env.
    environment: str = "production"
    database_url: str
    # Not used by any feature yet; reserved for signing tokens in later phases.
    secret_key: str
    cors_origins: str = "http://localhost:5173"
    session_ttl_minutes: int = 720
    # Number of reverse proxies in front of the API that append to X-Forwarded-For (Render: see README).
    # 0 ignores the header and uses the socket address.
    trusted_proxy_hops: int = Field(default=1, ge=0, le=5)
    # Password hashing uses ~64 MiB per call; this caps how many run at once so a burst of logins
    # cannot exhaust a small instance's memory.
    password_hash_concurrency: int = Field(default=2, ge=1, le=16)
    # Optional first-run bootstrap: creates this admin only if the users table is empty.
    admin_email: str | None = None
    admin_password: str | None = None

    @field_validator("environment")
    @classmethod
    def known_environment(cls, v: str) -> str:
        v = v.strip().lower()
        if v not in ("development", "production"):
            # A typo such as "prod" must not silently switch off production protections.
            raise ValueError("ENVIRONMENT must be 'development' or 'production'")
        return v

    @field_validator("database_url")
    @classmethod
    def use_psycopg3_driver(cls, v: str) -> str:
        # Neon/Render hand out postgres:// or postgresql:// URLs; SQLAlchemy needs the driver named.
        for prefix in ("postgres://", "postgresql://"):
            if v.startswith(prefix):
                return "postgresql+psycopg://" + v[len(prefix):]
        return v

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def is_production(self) -> bool:
        return self.environment == "production"


@lru_cache
def get_settings() -> Settings:
    return Settings()
