"""
logger.py - Loguru-based logging configuration.

Provides a pre-configured logger with colored console output.
"""

import sys
from loguru import logger

# Remove default handler
logger.remove()

# Console handler with colors
logger.add(
    sys.stderr,
    format=(
        "<green>{time:HH:mm:ss}</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
        "<level>{message}</level>"
    ),
    level="INFO",
    colorize=True,
)

# File handler with rotation
logger.add(
    "agent_debug.log",
    format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
    level="DEBUG",
    rotation="5 MB",
    retention="3 days",
    encoding="utf-8",
)

__all__ = ["logger"]
