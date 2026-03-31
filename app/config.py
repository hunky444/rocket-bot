from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    bot_token: str = Field(alias="BOT_TOKEN")
    api_id: int | None = Field(default=None, alias="API_ID")
    api_hash: str | None = Field(default=None, alias="API_HASH")
    session_name: str = Field(default="gift_analyst", alias="SESSION_NAME")
    admin_ids: str = Field(default="", alias="ADMIN_IDS")
    default_timezone: str = Field(default="Europe/Warsaw", alias="DEFAULT_TIMEZONE")
    database_path: str = Field(default="bot.db", alias="DATABASE_PATH")
    assets_dir: str = Field(default="assets", alias="ASSETS_DIR")
    webapp_host: str = Field(default="127.0.0.1", alias="WEBAPP_HOST")
    webapp_port: int = Field(default=8080, alias="WEBAPP_PORT")
    webapp_url: str = Field(default="https://example.com/webapp", alias="WEBAPP_URL")
    webapp_dev_mode: bool = Field(default=True, alias="WEBAPP_DEV_MODE")

    @property
    def admin_id_list(self) -> list[int]:
        if not self.admin_ids.strip():
            return []
        return [int(item.strip()) for item in self.admin_ids.split(",") if item.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
