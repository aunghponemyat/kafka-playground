import logging
import os
from datetime import datetime
from logging import StreamHandler
from logging.handlers import SysLogHandler
from typing import Any, Dict

import structlog
from colorama import Fore, Style

from kafka_test.models.config import Settings, get_settings

settings: Settings = get_settings()

class EventLogger(structlog.BoundLoggerBase):
    def info(self, event: str, **event_kw: Dict) -> Any:
        if "timestamp" not in event_kw:
            event_kw["timestamp"] = datetime.utcnow().isoformat()
        event_dict: Dict = event_kw
        return self._proxy_to_logger("info", event, **event_dict)

    def error(self, event: str, **event_kw: Dict) -> Any:
        if "timestamp" not in event_kw:
            event_kw["timestamp"] = datetime.utcnow().isoformat()
        event_dict: Dict = event_kw
        return self._proxy_to_logger("error", event, **event_dict)

    def exception(self, event: str, **event_kw: Dict) -> Any:
        if "exc" in event_kw.keys():
            exc: Any = event_kw["exc"]
            if isinstance(exc, Exception):
                event_kw["exc"] = {
                    "exception.type": f"{exc.__class__.__name__}",
                    "exception.message": str(exc),
                }
            event_kw["error"] = True
        self.error(event, **event_kw)

def custom_order_processor(_, __, event_dict):
    if "event" in event_dict:
        event = event_dict.pop("event")
        if "worker" in event_dict:
            worker = event_dict.pop("worker")
            event_dict = {"worker": worker, "event": event, **event_dict}
        else:
            event_dict = {"event": event, **event_dict}
    return event_dict

base_dir = os.path.dirname(os.path.realpath('.env'))
log_path = os.path.join(base_dir, 'logs/')
log_file_path = f"{log_path}{settings.log_directory}"

syslog_handler = SysLogHandler(address="/dev/log")
formatter = logging.Formatter('session %(name)s %(asctime)s [%(levelname)-8s] %(message)s')
syslog_handler.setFormatter(formatter)

class ColoredFormatter(logging.Formatter):
    LOG_COLORS = {
        "INFO": Fore.GREEN,
        "WARNING": Fore.YELLOW,
        "ERROR": Fore.RED,
        "CRITICAL": Fore.RED + Style.BRIGHT,
        "DEBUG": Fore.CYAN,
    }

    def format(self, record):
        color = self.LOG_COLORS.get(record.levelname, "")
        message = super().format(record)
        return color + message + Style.RESET_ALL

color_formatter = ColoredFormatter(
    "%(asctime)s [%(levelname)-8s] %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
)
stream_handler = StreamHandler()
stream_handler.setFormatter(color_formatter)

logging.basicConfig(
    format="%(asctime)s [%(levelname)-8s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    level=logging.INFO,
    handlers=[syslog_handler, stream_handler, logging.FileHandler(log_file_path)],
)

def custom_key_value_renderer(_, __, event_dict):
    parts = []
    for key, value in event_dict.items():
        if key == "worker":
            # Directly add the worker value without a key
            parts.append(str(value))
        else:
            parts.append(f"{key}='{value}'")
    return ' '.join(parts)

# Configure structlog
structlog.configure(
    processors=[
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.UnicodeDecoder(),
        custom_order_processor,
        custom_key_value_renderer,
        
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=EventLogger,
    cache_logger_on_first_use=True,
)