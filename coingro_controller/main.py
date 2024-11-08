#!/usr/bin/env python3
"""
Main Coingro bot script.
Read the documentation to know what cli arguments you need.
"""
import logging
import sys
from typing import Any, List, Optional

# check min. python version
if sys.version_info < (3, 8):  # pragma: no cover
    sys.exit("Coingro requires Python version >= 3.8")

from coingro.exceptions import CoingroException, OperationalException
from coingro.loggers import setup_logging_pre
from coingro_controller.commands import ControllerArguments

logger = logging.getLogger("coingro-controller")


def main(sysargv: Optional[List[str]] = None) -> None:
    """
    This function will initiate the bot and start the trading loop.
    :return: None
    """

    return_code: Any = 1
    try:
        setup_logging_pre()
        arguments = ControllerArguments(sysargv)
        args = arguments.get_parsed_arg()

        # Call subcommand.
        if "func" in args:
            return_code = args["func"](args)
        else:
            # No subcommand was issued.
            raise OperationalException(
                "Usage of Coingro controller requires a subcommand to be specified.\n"
                "To see the full list of options available, please use "
                "`coingro-controller --help` or `coingro-controller <command> --help`."
            )

    except SystemExit as e:  # pragma: no cover
        return_code = e
    except KeyboardInterrupt:
        logger.info("SIGINT received, aborting ...")
        return_code = 0
    except CoingroException as e:
        logger.error(str(e))
        return_code = 2
    except Exception:
        logger.exception("Fatal exception!")
    finally:
        sys.exit(return_code)


if __name__ == "__main__":  # pragma: no cover
    main()
