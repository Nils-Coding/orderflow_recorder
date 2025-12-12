from functools import lru_cache
from typing import List, Union

from pydantic import AliasChoices, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables and optional .env file.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="",
        case_sensitive=False,
        extra="ignore",
    )

    binance_ws_futures_base_url: str = "wss://fstream.binance.com/stream"
    
    # Allow passing comma-separated string which gets parsed to list
    symbols_futures: Union[List[str], str] = ["btcusdt", "ethusdt"]
    
    futures_streams_depth: str = "depth5@100ms"
    futures_streams_trades: str = "aggTrade"

    gcs_bucket_name: str = Field(
        default="orderflow-data-lake",
        validation_alias=AliasChoices("GCS_BUCKET_NAME", "gcs_bucket_name"),
    )
    
    buffer_seconds: int = Field(
        default=60,
        validation_alias=AliasChoices("BUFFER_SECONDS", "buffer_seconds"),
    )

    log_level: str = Field(
        default="INFO",
        validation_alias=AliasChoices("LOG_LEVEL", "log_level"),
    )

    api_key: str = Field(
        default="",
        validation_alias=AliasChoices("API_KEY", "api_key"),
        description="Secret key to protect the API"
    )

    @field_validator("symbols_futures")
    @classmethod
    def parse_symbols_list(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str):
            # Split by comma and strip whitespace
            return [s.strip() for s in v.split(",") if s.strip()]
        return v


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
