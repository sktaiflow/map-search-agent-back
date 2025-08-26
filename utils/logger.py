import sys
import logging

from datetime import datetime

from configs import config
from utils import json
from utils.timezone import KST

BUILTIN_ATTRS = {
    "args",
    "asctime",
    "created",
    "exc_info",
    "exc_text",
    "filename",
    "funcName",
    "levelname",
    "levelno",
    "lineno",
    "module",
    "msecs",
    "message",
    "msg",
    "name",
    "pathname",
    "process",
    "processName",
    "relativeCreated",
    "stack_info",
    "thread",
    "threadName",
    "taskName",
}


class AppLogFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord):
        """
        Format a record into a log entry string.

        The log entry string contains the following information:

        - level: log level (e.g. INFO, WARNING, ERROR)
        - app: application name
        - version: application version
        - datetime: current time in ISO format
        - type: log type (e.g. "message", "error")
        - message: log message
        - error: error information (if applicable)

        :param record: a LogRecord object
        :return: a formatted log entry string
        """

        extra = {
            attr: record.__dict__[attr] for attr in record.__dict__ if attr not in BUILTIN_ATTRS
        }

        if "type" not in extra:
            extra["type"] = "message"

        log = {
            "level": record.levelname,
            "app": config.app_name,
            "version": config.app_version,
            "datetime": datetime.now(KST).isoformat("T"),
            **extra,
        }

        if message := record.getMessage():
            log["message"] = message

        if record.exc_info:
            log["error"] = self.formatException(record.exc_info)

        return json.dumps(log, default=str)


logger = logging.getLogger("app")
handler = logging.StreamHandler(stream=sys.stdout)
handler.setFormatter(AppLogFormatter())
logger.addHandler(handler)
logger.setLevel(logging.INFO)
