import logging
import os
from typing import Any, Dict

from coingro.exceptions import OperationalException
from coingro_controller import __env__

logger = logging.getLogger(__name__)


def start_controller(args: Dict[str, Any]) -> int:
    """
    Main entry point for controller
    """
    # Import here to avoid loading worker module when it's not used
    from coingro_controller.worker import Worker

    if __env__ != "kubernetes" or "KUBERNETES_SERVICE_HOST" not in os.environ:
        raise OperationalException("Coingro controller must be run within a " "kubernetes cluster.")

    # Create and run worker
    worker = None
    try:
        worker = Worker(args)
        worker.run()
    except Exception as e:
        logger.error(str(e))
        logger.exception("Fatal exception!")
    except KeyboardInterrupt:
        logger.info("SIGINT received, aborting ...")
    finally:
        if worker:
            logger.info("worker found ... calling exit")
            worker.exit()
    return 0
