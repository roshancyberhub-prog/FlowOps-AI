import logging

from pythonjsonlogger.json import JsonFormatter


def json_handler() -> logging.Handler:
    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter("%(asctime)s %(levelname)s %(name)s %(message)s"))
    return handler


def configure_logging() -> None:
    logger = logging.getLogger("flowops")
    logger.handlers = [json_handler()]
    logger.setLevel(logging.INFO)
    logger.propagate = False
