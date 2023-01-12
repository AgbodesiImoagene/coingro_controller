import logging
from logging import Formatter
from logging.handlers import RotatingFileHandler, SysLogHandler
from pathlib import Path
from typing import Any, Dict

from coingro.constants import USERPATH_LOGS
from coingro.exceptions import OperationalException
from coingro.loggers import CGBufferingHandler
from coingro_controller.constants import USER_DATA_DIR

logger = logging.getLogger(__name__)
LOGFORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

# Initialize bufferhandler - will be used for /log endpoints
bufferHandler = CGBufferingHandler(1000)
bufferHandler.setFormatter(Formatter(LOGFORMAT))


def _set_loggers(verbosity: int = 0, api_verbosity: str = "info") -> None:
    """
    Set the logging level for third party libraries
    :return: None
    """

    logging.getLogger("requests").setLevel(logging.INFO if verbosity <= 1 else logging.DEBUG)
    logging.getLogger("urllib3").setLevel(logging.INFO if verbosity <= 1 else logging.DEBUG)
    logging.getLogger("telegram").setLevel(logging.INFO)

    logging.getLogger("werkzeug").setLevel(
        logging.ERROR if api_verbosity == "error" else logging.INFO
    )


def get_existing_handlers(handlertype):
    """
    Returns Existing handler or None (if the handler has not yet been added to the root handlers).
    """
    return next((h for h in logging.root.handlers if isinstance(h, handlertype)), None)


def setup_logging(config: Dict[str, Any]) -> None:
    """
    Process -v/--verbose, --logfile options
    """
    # Log level
    verbosity = config["verbosity"]
    if not get_existing_handlers(CGBufferingHandler):
        logging.root.addHandler(bufferHandler)

    logfile = config.get("logfile")

    if logfile:
        s = logfile.split(":")
        if s[0] == "syslog":
            # Address can be either a string (socket filename) for Unix domain socket or
            # a tuple (hostname, port) for UDP socket.
            # Address can be omitted (i.e. simple 'syslog' used as the value of
            # config['logfilename']), which defaults to '/dev/log', applicable for most
            # of the systems.
            address = (s[1], int(s[2])) if len(s) > 2 else s[1] if len(s) > 1 else "/dev/log"
            handler_sl = get_existing_handlers(SysLogHandler)
            if handler_sl:
                logging.root.removeHandler(handler_sl)
            handler_sl = SysLogHandler(address=address)
            # No datetime field for logging into syslog, to allow syslog
            # to perform reduction of repeating messages if this is set in the
            # syslog config. The messages should be equal for this.
            handler_sl.setFormatter(Formatter("%(name)s - %(levelname)s - %(message)s"))
            logging.root.addHandler(handler_sl)
        elif s[0] == "journald":  # pragma: no cover
            try:
                from systemd.journal import JournaldLogHandler
            except ImportError:
                raise OperationalException(
                    "You need the systemd python package be installed in "
                    "order to use logging to journald."
                )
            handler_jd = get_existing_handlers(JournaldLogHandler)
            if handler_jd:
                logging.root.removeHandler(handler_jd)
            handler_jd = JournaldLogHandler()
            # No datetime field for logging into journald, to allow syslog
            # to perform reduction of repeating messages if this is set in the
            # syslog config. The messages should be equal for this.
            handler_jd.setFormatter(Formatter("%(name)s - %(levelname)s - %(message)s"))
            logging.root.addHandler(handler_jd)
        else:
            import coingro_controller

            if logfile == "default" or coingro_controller.__env__ == "kubernetes":
                logdir = f'{config.get("user_data_dir", USER_DATA_DIR)}/{USERPATH_LOGS}/'
                logfile = f"{coingro_controller.__id__}.log"
                if Path(logdir).is_dir():
                    logfile = logdir + logfile
            handler_rf = get_existing_handlers(RotatingFileHandler)
            if handler_rf:
                logging.root.removeHandler(handler_rf)
            handler_rf = RotatingFileHandler(
                logfile, maxBytes=1024 * 1024 * 10, backupCount=10  # 10Mb
            )
            handler_rf.setFormatter(Formatter(LOGFORMAT))
            logging.root.addHandler(handler_rf)

    logging.root.setLevel(logging.INFO if verbosity < 1 else logging.DEBUG)
    _set_loggers(verbosity, config.get("api_server", {}).get("verbosity", "info"))

    logger.info("Verbosity set to %s", verbosity)
