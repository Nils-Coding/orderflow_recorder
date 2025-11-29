import sys
from typing import Optional

from loguru import logger as _logger

from orderflow_recorder.config.settings import get_settings


DEFAULT_FORMAT = (
	"<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
	"<level>{level: <8}</level> | "
	"<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
	"<level>{message}</level>"
)


def setup_logging(level: Optional[str] = None) -> None:
	"""
	Configure loguru using Settings.LOG_LEVEL unless an explicit level is provided.
	"""
	settings = get_settings()
	effective_level = (level or settings.log_level or "INFO").upper()

	_logger.remove()
	_logger.add(
		sys.stderr,
		level=effective_level,
		format=DEFAULT_FORMAT,
		enqueue=True,
		backtrace=False,
		diagnose=False,
	)


def get_logger():
	return _logger


