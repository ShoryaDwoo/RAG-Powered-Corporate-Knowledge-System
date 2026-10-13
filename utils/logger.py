"""Centralised loguru logger configuration."""
import sys
from loguru import logger
from config import cfg

logger.remove()
logger.add(
    sys.stdout,
    level=cfg.log_level,
    format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan> — {message}",
    colorize=True,
)
logger.add(
    "logs/pipeline.log",
    level="DEBUG",
    rotation="10 MB",
    retention="14 days",
    compression="gz",
)
