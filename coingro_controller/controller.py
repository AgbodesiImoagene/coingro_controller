"""
Main Coingro controller class.
"""
import logging
from datetime import datetime
from typing import Any, Dict, Optional

from coingro.enums import State
from coingro.mixins import LoggingMixin

from coingro_controller import __version__
from coingro_controller.k8s import Client
from coingro_controller.misc import generate_uid
from coingro_controller.persistence import Bot, cleanup_db, init_db
from coingro_controller.rpc import CoingroClient, RPCManager
from coingro_controller.strategy_manager import StrategyManager


logger = logging.getLogger(__name__)


class Controller(LoggingMixin):
    def __init__(self, config: Dict[str, Any]) -> None:
        logger.info('Starting coingro controller %s', __version__)

        self.state = State.STOPPED

        self.config = config
        self.coingro_client = CoingroClient(self.config)
        init_db(self.config['db_url'])
        self.k8s_client = Client(self.config)

        self.rpc: RPCManager = RPCManager(self)
        self.strategy_manager: StrategyManager = StrategyManager(self)
        LoggingMixin.__init__(self, logger)

        initial_state = self.config.get('initial_state')
        self.state = State[initial_state.upper()] if initial_state else State.STOPPED

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
        self.strategy_manager.refresh()

    def process_stopped(self) -> None:
        """
        Close all orders that were left open
        """
        pass

    def check_bots(self) -> None:
        active_bots = Bot.get_active_bots()
        active_bot_names = [bot.bot_id for bot in active_bots]

        for bot_name in active_bot_names:
            self.create_bot(bot_name)

    def create_bot(self,
                   name: Optional[str] = None,
                   user: Optional[str] = None,
                   is_strategy: bool = False,
                   env_vars: Optional[Dict[str, Any]] = None) -> Optional[str]:
        if not name:
            uid = generate_uid()
            name = f'coingro-bot-{uid}'
            while Bot.bot_by_id(name):
                uid = generate_uid()
                name = f'coingro-bot-{uid}'

        bot = Bot.bot_by_id(name)

        running_bots = self.k8s_client.get_coingro_instances()
        running_bot_names = [bot['metadata']['name'] for bot in running_bots]

        deleted = True if bot and bot.deleted_at else False

        if name not in running_bot_names and not deleted:
            self.k8s_client.create_coingro_instance(name, env_vars)

            if bot:
                bot.is_active = True
            else:
                bot = Bot(bot_id=name,
                          user_id=user,
                          image=self.config['cg_image'],
                          version=self.config['cg_version'],
                          is_strategy=is_strategy)
            Bot.query.session.add(bot)
            Bot.commit()

        return bot.bot_id if bot else None

    def deactivate_bot(self, name: str, delete: bool = False):
        bot = Bot.bot_by_id(name)
        if bot:
            running_bots = self.k8s_client.get_coingro_instances()
            running_bot_names = [bot['metadata']['name'] for bot in running_bots]
            if name in running_bot_names:
                self.k8s_client.delete_coingro_instance(name)

            bot.is_active = False
            if delete:
                bot.deleted_at = datetime.utcnow()
            Bot.commit()
