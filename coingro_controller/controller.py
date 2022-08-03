"""
Main Coingro controller class.
"""
import logging
from datetime import datetime
# from time import sleep
from typing import Any, Dict, Optional

from coingro.enums import State
from coingro.mixins import LoggingMixin

from coingro_controller import __version__
from coingro_controller.k8s import Client
from coingro_controller.misc import generate_uid
from coingro_controller.persistence import Bot, Strategy, cleanup_db, init_db
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

        self.state = State.RUNNING
        # sleep(120)  # Give pods enough time to startup. Find better method.

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

        for bot in active_bots:
            bot_id = bot.bot_id
            instance = self.k8s_client.get_coingro_instance(bot_id.lower())
            status = instance.status.phase if instance else None
            if status != 'Running':
                if bot.is_strategy:
                    strategy = Strategy.strategy_by_bot_id(bot_id)
                    env = {
                        'COINGRO__STRATEGY': strategy.name,
                        'COINGRO__INITIAL_STATE': 'running'
                    } if strategy else None
                    self.create_bot(bot_id, env_vars=env)
                else:
                    self.create_bot(bot_id)

    def create_bot(self,
                   name: Optional[str] = None,
                   user: Optional[str] = None,
                   is_strategy: bool = False,
                   env_vars: Optional[Dict[str, Any]] = None) -> Optional[str]:
        if not name:
            uid = generate_uid()
            name = f'bot-{uid}'
            while Bot.bot_by_id(name):
                uid = generate_uid()
                name = f'bot-{uid}'

        name = name.lower()

        bot = Bot.bot_by_id(name)

        instance = self.k8s_client.get_coingro_instance(name)
        status = instance.status.phase if instance else None
        is_deleted = True if bot and bot.deleted_at else False

        if instance:
            logger.info(f'Bot {name} status: {status}')

        if status != 'Running' and not is_deleted:
            if instance:
                self.k8s_client.replace_coingro_instance(name, env_vars)
                logger.info(f"Restarted coingro instance {name}.")
            else:
                self.k8s_client.create_coingro_instance(name, env_vars)
                logger.info(f"Created coingro instance {name}.")

            if not bot:
                bot = Bot(bot_id=name,
                          user_id=user,
                          is_strategy=is_strategy)

                if is_strategy:
                    bot.state = State['RUNNING']
                elif 'cg_initial_state' in self.config:
                    bot.state = State[self.config['cg_initial_state'].upper()]

            bot.is_active = True
            bot.image = self.config['cg_image']
            bot.version = self.config['cg_version']
            bot.api_url = f"http://{name}/{self.config['cg_api_router_prefix']}" \
                          if 'cg_api_router_prefix' in self.config else f'http://{name}'
            Bot.query.session.add(bot)
            Bot.commit()

        return bot.bot_id if bot else None

    def deactivate_bot(self, name: str, delete: bool = False):
        bot = Bot.bot_by_id(name)
        if bot:
            self.k8s_client.delete_coingro_instance(name)
            logger.info(f"Deleted coingro instance {name}.")

            bot.is_active = False
            if delete:
                bot.deleted_at = datetime.utcnow()
            Bot.commit()
        return bot.bot_id if bot else None
