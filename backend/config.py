"""
FinVoice — Application Configuration
Loads settings from environment variables via Pydantic BaseSettings.
"""

from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # ─── App ───
    app_name: str = "FinVoice"
    app_env: str = "development"
    secret_key: str = "change-me-in-production"
    cors_origins: str = "http://localhost:3000"

    # ─── Database ───
    database_url: str = "postgresql+asyncpg://finvoice:finvoice_dev@localhost:5432/finvoice"
    database_url_sync: str = "postgresql://finvoice:finvoice_dev@localhost:5432/finvoice"

    # ─── Redis ───
    redis_url: str = "redis://localhost:6379/0"

    # ─── Supabase Auth ───
    supabase_url: str = ""
    supabase_key: str = ""
    supabase_jwt_secret: str = ""

    # ─── Angel One (Broker) ───
    angel_one_api_key: str = ""
    angel_one_client_id: str = ""
    angel_one_password: str = ""
    angel_one_totp_secret: str = ""

    # ─── Trading ───
    trading_enabled: bool = True                    # Master kill switch
    paper_trading_initial_balance: float = 1000000.0  # ₹10 lakh
    max_daily_trades: int = 20
    max_single_order_pct: float = 25.0
    daily_loss_limit_pct: float = 3.0

    # ─── Vapi.ai (Voice) ───
    vapi_api_key: str = ""
    vapi_assistant_id: str = ""

    # ─── LLM ───
    google_ai_api_key: str = ""
    openai_api_key: str = ""

    # ─── MLflow ───
    mlflow_tracking_uri: str = "http://localhost:5000"

    # ─── Razorpay ───
    razorpay_key_id: str = ""
    razorpay_key_secret: str = ""

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",")]

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"


@lru_cache
def get_settings() -> Settings:
    return Settings()
