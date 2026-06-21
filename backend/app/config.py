"""Central configuration, loaded from environment (.env). No secrets in code."""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    domain: str = "localhost"
    admin_email: str = "you@example.com"
    session_secret: str = "change-me"
    redis_url: str = "redis://redis:6379/0"

    download_dir: str = "/downloads"
    cookies_file: str = "/secrets/cookies.txt"
    user_cookies_dir: str = "/usercookies"
    data_dir: str = "/data"
    file_ttl_hours: int = 6

    max_filesize_mb: int = 2048
    max_duration_min: int = 240
    max_concurrent_downloads: int = 2

    rate_limit_login: int = 10
    rate_limit_submit: int = 20

    @property
    def max_filesize_bytes(self) -> int:
        return self.max_filesize_mb * 1024 * 1024


settings = Settings()
