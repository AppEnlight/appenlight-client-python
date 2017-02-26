import logging

log = logging.getLogger(__name__)

EXCLUDED_LOG_VARS = [
    'threadName', 'name', 'thread', 'created', 'process', 'processName', 'args',
    'module', 'filename', 'levelno', 'exc_text', 'pathname', 'lineno', 'msg',
    'exc_info', 'message', 'funcName', 'relativeCreated', 'levelname',
    'msecs', 'asctime', 'stack_info']


def register_logging(logger, client_config, cls):
    found = False
    for handler in logger.handlers:
        if isinstance(handler, cls):
            found = True
            reg_handler = handler
    if not found:
        reg_handler = cls(client_config=client_config)
        logger.addHandler(reg_handler)
    return reg_handler


def unregister_logger(logger, handler):
    logger.removeHandler(handler)
