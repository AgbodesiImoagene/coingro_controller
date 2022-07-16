"""
Main Coingro controller class.
"""
import logging
import time
import traceback
from os import getpid
from pathlib import Path
from typing import Any, Callable, Dict, Optional

import sdnotify

# from kubernetes import client, config

from coingro.coingrobot import CoingroBot
from coingro.configuration import Configuration
from coingro.constants import (DEFAULT_CONFIG_SAVE, PROCESS_THROTTLE_SECS, RETRY_TIMEOUT,
                               USERPATH_STRATEGIES)
from coingro.enums import State
from coingro.exceptions import OperationalException, TemporaryError
from coingro.mixins import LoggingMixin
from coingro.resolvers import StrategyResolver

from coingro_controller import __env__, __version__
from coingro_controller.k8s import Client
from coingro_controller.persistence import Bot, User, cleanup_db, init_db
from coingro_controller.rpc import CoingroClient, RPCManager


logger = logging.getLogger(__name__)


class Controller(LoggingMixin):
    def __init__(self, config: Dict[str, Any]) -> None:
        logger.info('Starting coingro controller %s', __version__)

        self.state = State.STOPPED

        self.config = config
        self.coingro_client = CoingroClient(self.config)
        init_db(self.config['db_url'])
        self.k8s_client = Client(self.config)
        # init_strategies(self.config['db_url'])

        self.rpc: RPCManager = RPCManager(self)
        LoggingMixin.__init__(self, logger)

        initial_state = self.config.get('initial_state')
        self.state = State[initial_state.upper()] if initial_state else State.STOPPED
        self.strategies = None

    def cleanup(self) -> None:
        """
        Cleanup pending resources on an already stopped bot
        :return: None
        """
        logger.info('Cleaning up modules ...')

        self.rpc.cleanup()
        cleanup_db()

    def startup(self) -> None:
        """
        Called on startup and after reloading the bot - performs startup tasks
        """
        pass

    def process(self) -> None:
        """
        Queries the persistence layer for open trades and handles them,
        otherwise a new trade is created.
        :return: True if one or more trades has been created or closed, False otherwise
        """
        self.check_bots()

    def process_stopped(self) -> None:
        """
        Close all orders that were left open
        """
        pass

    def check_bots(self) -> None:
        active_bots = Bot.get_active_bots()
        active_bot_names = [bot.bot_id for bot in active_bots]

        running_bots = self.k8s_client.get_coingro_instances()
        running_bot_names = [bot['metadata']['name'] for bot in running_bots]

        for bot_name in active_bot_names:
            if bot_name not in running_bot_names:
                self.k8s_client.create_coingro_instances(bot_name)

    def init_strategies(self) -> None:
        strategies = self.list_strategies()

    def get_strategies() -> None:
        directory = Path(self.config.get('strategy_path', USERPATH_STRATEGIES))
        return StrategyResolver.search_all_objects(
            directory, False, self.config.get('recursive_strategy_search', False))

