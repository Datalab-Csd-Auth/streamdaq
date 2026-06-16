import logging
import sys
from typing import Optional, Union

DEFAULT_LOG_FORMAT = "[%(asctime)s] [%(levelname)s] [%(name)s]: %(message)s"
DEFAULT_DATE_FORMAT = "%Y-%m-%dT%H:%M:%S"

def configure_logging(
    level: Union[int, str] = logging.INFO,
    pathway_level: Optional[Union[int, str]] = logging.WARNING,
    enable_console: bool = True,
    log_format: str = DEFAULT_LOG_FORMAT,
    date_format: str = DEFAULT_DATE_FORMAT
) -> None:
    """
    Bootstrap entry point for StreamDaQ logging isolation.
    
    Enforces independent granularity between StreamDaQ and the underlying engine,
    and shields the host application's root logger from library pollution.
    """
    # Fetch the top-level parent logger for the entire library
    sd_logger = logging.getLogger("streamdaq")
    sd_logger.setLevel(level)

    # SEVER ROOT POLLUTION
    # Prevent any submodules ('streamdaq.validation', etc.) from bubbling 
    # up past the parent 'streamdaq' namespace into the user's global root logger.
    sd_logger.propagate = False

    # Isolate or adjust Pathway execution logs
    pw_logger = logging.getLogger("pathway_engine")
    if pathway_level is None:
        pw_logger.handlers = [logging.NullHandler()]
        pw_logger.propagate = False
    else:
        pw_logger.setLevel(pathway_level)
        pw_logger.propagate = True

    if not enable_console:
        return
        
    # Prevent handler accumulation if configure_logging is called multiple times
    # Note: Using [:] snapshot copy to prevent skipping elements when mutating the list in-place
    for handler in sd_logger.handlers[:]:
        if isinstance(handler, logging.StreamHandler):
            sd_logger.removeHandler(handler)

    console_handler = logging.StreamHandler(sys.stdout)
    formatter = logging.Formatter(fmt=log_format, datefmt=date_format)
    console_handler.setFormatter(formatter)
    sd_logger.addHandler(console_handler)
