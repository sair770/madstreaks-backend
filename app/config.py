import logging
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    groww_api_key: str
    groww_api_secret: str
    groww_totp_secret: str
    telegram_bot_token: str
    telegram_chat_id: int
    telegram_channel_id: int
    supabase_url: str
    supabase_service_key: str
    briefing_api_key: str = "sk-briefing-dev-key-change-in-prod"
    port: int = 8000
    env: str = "production"
    log_level: str = "INFO"

    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()

logging.basicConfig(
    level=settings.log_level,
    format="%(asctime)s — %(name)s — %(levelname)s — %(message)s"
)
logger = logging.getLogger(__name__)
