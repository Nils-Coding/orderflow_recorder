from functools import lru_cache
from typing import List

from pydantic import AliasChoices, Field
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
	symbols_futures: List[str] = ["btcusdt", "ethusdt"]
	futures_streams_depth: str = "depth5@100ms"
	futures_streams_trades: str = "aggTrade"

	db_url: str = Field(
		default="postgresql+psycopg2://postgres:postgres@localhost:5432/orderflow_recorder",
		validation_alias=AliasChoices("DB_URL", "db_url"),
	)

	log_level: str = Field(
		default="INFO",
		validation_alias=AliasChoices("LOG_LEVEL", "log_level"),
	)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
	return Settings()


