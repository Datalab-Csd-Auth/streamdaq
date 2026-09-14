import logging


def get_logger(module_name: str) -> logging.Logger:
    """
    Internal helper: returns a namespaced logger.

    Ensures the hierarchy is preserved and propagation behaves predictably.
    """
    logger = logging.getLogger(module_name)
    # Ensure child loggers don't duplicate logs up to a misconfigured root
    # if the host application turns on propagation later.
    logger.propagate = True
    return logger
