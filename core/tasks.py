import logging
import traceback

from app.celery import app

logger = logging.getLogger()
logger.setLevel(logging.INFO)
# Create handlers
c_handler = logging.StreamHandler()
c_handler.setLevel(logging.INFO)

# Create formatters and add it to handlers
c_format = logging.Formatter(
    "%(asctime)s :: %(levelname)s :: %(message)s",
    datefmt="%d-%m-%Y %H:%M:%S",
)
c_handler.setFormatter(c_format)

# Add handlers to the logger
logger.addHandler(c_handler)
