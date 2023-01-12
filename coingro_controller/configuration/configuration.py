"""
This module contains the configuration class
"""
import logging
import os
import warnings
from copy import deepcopy
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from packaging.version import InvalidVersion, parse
from sqlalchemy.engine import URL

from coingro.configuration.config_security import Encryption
from coingro.configuration.directory_operations import create_userdata_dir
from coingro.configuration.environment_vars import flat_vars_to_nested_dict
from coingro.configuration.load_config import load_config_file
from coingro.exceptions import OperationalException
from coingro.misc import deep_merge_dicts, parse_db_uri_for_logging
from coingro_controller.constants import DEFAULT_DB_URL, ENV_VAR_PREFIX
from coingro_controller.loggers import setup_logging

logger = logging.getLogger(__name__)


class Configuration:
    """
    Class to read and init the bot configuration
    Reuse this class for the bot, backtesting, hyperopt and every script that required configuration
    """

    def __init__(self, args: Dict[str, Any]) -> None:
        self.args = args
        self.config: Optional[Dict[str, Any]] = None

    def get_config(self) -> Dict[str, Any]:
        """
        Return the config. Use this method to get the bot config
        :return: Dict: Bot config
        """
        if self.config is None:
            self.config = self.load_config()

        return self.config

    @staticmethod
    def from_files(files: List[str]) -> Dict[str, Any]:
        """
        Iterate through the config files passed in, loading all of them
        and merging their contents.
        Files are loaded in sequence, parameters in later configuration files
        override the same parameter from an earlier file (last definition wins).
        Runs through the whole Configuration initialization, so all expected config entries
        are available to interactive environments.
        :param files: List of file paths
        :return: configuration dictionary
        """
        # Keep this method as staticmethod, so it can be used from interactive environments
        c = Configuration({"config": files})
        return c.get_config()

    def load_config(self) -> Dict[str, Any]:
        """
        Extract information for sys.argv and load the bot configuration
        :return: Configuration dictionary
        """
        # Load all configs
        config_files = self.args.get("config", [])
        config: Dict[str, Any] = load_from_files(config_files)
        config = Encryption(config).get_plain_config()

        # Load environment variables
        env_data = enironment_vars_to_dict()
        config = deep_merge_dicts(env_data, config)

        # Normalize config
        if "internals" not in config:
            config["internals"] = {}

        if "original_config_files" not in config:
            config["original_config_files"] = config_files

        # Keep a copy of the original configuration file
        if "original_config" not in config:
            config["original_config"] = deepcopy(config)

        self._process_logging_options(config)

        self._process_common_options(config)

        self._process_coingro_options(config)

        self._process_datadir_options(config)

        self._process_database_options(config)

        return config

    def _process_logging_options(self, config: Dict[str, Any]) -> None:
        """
        Extract information for sys.argv and load logging configuration:
        the -v/--verbose, --logfile options
        """
        # Log level
        config.update({"verbosity": self.args.get("verbosity", 0)})

        if "logfile" in self.args and self.args["logfile"]:
            config.update({"logfile": self.args["logfile"]})

        setup_logging(config)

    def _process_database_options(self, config: Dict[str, Any]) -> None:
        config["db_url"] = Configuration.db_url_from_config(config)

        logger.info(f'Using DB: "{parse_db_uri_for_logging(config["db_url"])}"')

    def _process_coingro_options(self, config: Dict[str, Any]) -> None:
        # cg_version = ''
        # if 'cg_version' in config:
        #     cg_version = config['cg_version']
        # else:
        #     cg_version = config['cg_image'].split(':')[-1]

        try:
            config["cg_version"] = str(parse(config["cg_version"]))
        except InvalidVersion:
            raise OperationalException("Invalid version provided.")

        logger.info(f'Using coingro image: "{config["cg_image"]}"')
        logger.info(f'Using coingro image version: "{config["cg_version"]}"')

    def _process_common_options(self, config: Dict[str, Any]) -> None:
        self._args_to_config(
            config, argname="strategy_path", logstring="Using additional Strategy lookup path: {}"
        )

        self._args_to_config(
            config,
            argname="recursive_strategy_search",
            logstring="Recursively searching for a strategy in the strategies folder.",
        )

        if "db_url" in self.args and self.args["db_url"]:
            config.update({"db_url": self.args["db_url"]})
            logger.info("Parameter --db-url detected ...")

        # Support for sd_notify
        if "sd_notify" in self.args and self.args["sd_notify"]:
            config["internals"].update({"sd_notify": True})

    def _process_datadir_options(self, config: Dict[str, Any]) -> None:
        """
        Extract information for sys.argv and load directory configurations
        --user-data, --datadir
        """
        if "user_data_dir" in self.args and self.args["user_data_dir"]:
            config.update({"user_data_dir": self.args["user_data_dir"]})
        elif "user_data_dir" not in config:
            # Default to /coingro/user_data (exists if base image is coingro)
            userdir = Path("/coingro/user_data")
            if not userdir.is_dir():
                userdir = Path("user_data")
            config.update({"user_data_dir": str(userdir)})

        # reset to user_data_dir so this contains the absolute path.
        config["user_data_dir"] = create_userdata_dir(config["user_data_dir"], create_dir=False)
        logger.info("Using user-data directory: %s ...", config["user_data_dir"])

    def _args_to_config(
        self,
        config: Dict[str, Any],
        argname: str,
        logstring: str,
        logfun: Optional[Callable] = None,
        deprecated_msg: Optional[str] = None,
    ) -> None:
        """
        :param config: Configuration dictionary
        :param argname: Argumentname in self.args - will be copied to config dict.
        :param logstring: Logging String
        :param logfun: logfun is applied to the configuration entry before passing
                        that entry to the log string using .format().
                        sample: logfun=len (prints the length of the found
                        configuration instead of the content)
        """
        if (
            argname in self.args
            and self.args[argname] is not None
            and self.args[argname] is not False
        ):

            config.update({argname: self.args[argname]})
            if logfun:
                logger.info(logstring.format(logfun(config[argname])))
            else:
                logger.info(logstring.format(config[argname]))
            if deprecated_msg:
                warnings.warn(f"DEPRECATED: {deprecated_msg}", DeprecationWarning)

    @staticmethod
    def db_url_from_config(config: Dict[str, Any]) -> str:
        if "db_url" in config:
            return config["db_url"]

        if "db_config" in config:
            db_args = deepcopy(config["db_config"])

            if db_args["drivername"] == "mysql":
                db_args["drivername"] = "mysql+pymysql"

            if db_args["drivername"] == "postgresql":
                db_args["drivername"] = "postgresql+psycopg2"

            if db_args["drivername"] != "sqlite" and "database" not in db_args:
                db_args["database"] = "coingro_k8s_controller"

            return URL.create(**db_args).render_as_string(hide_password=False)

        return DEFAULT_DB_URL


def load_from_files(
    files: List[str], base_path: Optional[Path] = None, level: int = 0
) -> Dict[str, Any]:
    """
    Recursively load configuration files if specified.
    Sub-files are assumed to be relative to the initial config.
    """
    config: Dict[str, Any] = {}
    if level > 5:
        raise OperationalException("Config loop detected.")

    if not files:
        return {}
    files_loaded = []
    # We expect here a list of config filenames
    for filename in files:
        logger.info(f"Using config: {filename} ...")
        if filename == "-":
            # Immediately load stdin and return
            return load_config_file(filename)
        file = Path(filename)
        if base_path:
            # Prepend basepath to allow for relative assignments
            file = base_path / file

        config_tmp = load_config_file(str(file))
        if "add_config_files" in config_tmp:
            config_sub = load_from_files(
                config_tmp["add_config_files"], file.resolve().parent, level + 1
            )
            files_loaded.extend(config_sub.get("config_files", []))
            config_tmp = deep_merge_dicts(config_tmp, config_sub)

        files_loaded.insert(0, str(file))

        # Merge config options, overwriting prior values
        config = deep_merge_dicts(config_tmp, config)

    config["config_files"] = files_loaded

    return config


def enironment_vars_to_dict() -> Dict[str, Any]:
    """
    Read environment variables and return a nested dict for relevant variables
    Relevant variables must follow the COINGRO_CONTROLLER__{section}__{key} pattern
    :return: Nested dict based on available and relevant variables.
    """
    return flat_vars_to_nested_dict(os.environ.copy(), ENV_VAR_PREFIX)
