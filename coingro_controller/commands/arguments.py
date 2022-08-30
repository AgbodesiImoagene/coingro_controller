import argparse
from pathlib import Path
from typing import Any, Dict, List, Optional

from coingro_controller.commands.cli_options import AVAILABLE_CLI_OPTIONS
from coingro_controller.constants import DEFAULT_CONFIG


ARGS_COMMON = ["verbosity", "logfile", "version", "config", "user_data_dir", "strategy_path",
               "db_url", "sd_notify"]


class ControllerArguments:
    def __init__(self, args: Optional[List[str]]) -> None:
        self.args = args
        self._parsed_arg: Optional[argparse.Namespace] = None

    def get_parsed_arg(self) -> Dict[str, Any]:
        """
        Return the list of arguments
        :return: List[str] List of arguments
        """
        if self._parsed_arg is None:
            self._build_subcommands()
            self._parsed_arg = self._parse_args()

        return vars(self._parsed_arg)

    def _parse_args(self) -> argparse.Namespace:
        """
        Parses given arguments and returns an argparse Namespace instance.
        """
        parsed_arg = self.parser.parse_args(self.args)

        # Workaround issue in argparse with action='append' and default value
        # (see https://bugs.python.org/issue16399)
        # Allow no-config for certain commands (like downloading / plotting)
        if ('config' in parsed_arg and parsed_arg.config is None):
            # Try loading from "config/config.json"
            cfgfile = Path('config') / DEFAULT_CONFIG
            if cfgfile.is_file():
                parsed_arg.config = [str(cfgfile)]
            else:
                # Else use "config.json".
                cfgfile = Path.cwd() / DEFAULT_CONFIG
                if cfgfile.is_file():
                    parsed_arg.config = [DEFAULT_CONFIG]

        return parsed_arg

    def _build_args(self, optionlist, parser):

        for val in optionlist:
            opt = AVAILABLE_CLI_OPTIONS[val]
            parser.add_argument(*opt.cli, dest=val, **opt.kwargs)

    def _build_subcommands(self) -> None:
        # Build main command
        self.parser = argparse.ArgumentParser(description='Coingro kubernetes orchestrator')
        self._build_args(optionlist=['version'], parser=self.parser)

        subparsers = self.parser.add_subparsers(dest='command',
                                                # Use custom message when no subhandler is added
                                                # shown from `main.py`
                                                # required=True
                                                )

        from coingro_controller.commands import start_controller

        # Add controller subcommand
        start_controller_cmd = subparsers.add_parser('start',
                                                     help='Start coingro controller '
                                                     'within kubernetes cluster.')
        start_controller_cmd.set_defaults(func=start_controller)
        self._build_args(optionlist=ARGS_COMMON, parser=start_controller_cmd)
