import sys
from typing import Any

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from orderflow_recorder.config.settings import get_settings, Settings
from orderflow_recorder.storage.models import Base
from orderflow_recorder.utils.logging import setup_logging, get_logger


def get_engine(settings: Settings):
	return create_engine(settings.db_url, pool_pre_ping=True, future=True)


def get_session_factory(engine) -> sessionmaker[Session]:
	return sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False, future=True)


def init_db(engine) -> None:
	Base.metadata.create_all(bind=engine)


def main(argv: list[str]) -> int:
	setup_logging()
	log = get_logger()
	if not argv:
		log.info("Usage: python -m orderflow_recorder.storage.db init-db")
		return 1

	cmd = argv[0]
	if cmd == "init-db":
		settings = get_settings()
		log.info(f"Initializing database schema at {settings.db_url}")
		engine = get_engine(settings)
		init_db(engine)
		log.info("Database schema created or already up-to-date.")
		return 0

	log.error(f"Unknown command: {cmd}")
	return 1


if __name__ == "__main__":
	raise SystemExit(main(sys.argv[1:]))


