"""
Main Coingro controller class.
"""
import logging
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd
from packaging.version import parse
from randomname import get_name

from coingro.configuration import Configuration
from coingro.enums import State
from coingro.mixins import LoggingMixin
from coingro.resolvers import StrategyResolver
from coingro_controller import __env__, __group__, __version__
from coingro_controller.constants import (
    BOT_NAME_ADJECTIVES,
    DEFAULT_EXCHANGE,
    DEFAULT_STAKE_CURRENCY,
)
from coingro_controller.k8s import Client
from coingro_controller.loggers import setup_logging
from coingro_controller.persistence import Bot, Strategy, cleanup_db, init_db
from coingro_controller.rpc import CoingroClient, RPCManager

logger = logging.getLogger(__name__)


class Controller(LoggingMixin):
    def __init__(self, config: Dict[str, Any]) -> None:
        logger.info("Starting coingro controller %s", __version__)

        self.state = State.STOPPED

        self.config = config
        self.default_bot_config = Configuration(
            {
                "config": ["/coingro/user_data/config/config.json"],
                "user_data_dir": "/coingro/user_data/",
                "strategy": "Strategy001",
            }
        ).get_config()
        setup_logging(
            self.config if "verbosity" in config else {"verbosity": 2}
        )  # get_config has side effect of updating global logging

        self.coingro_client = CoingroClient(self.config)
        init_db(self.config["db_url"])
        self.k8s_client = Client(self.config)

        self.rpc: RPCManager = RPCManager(self)
        LoggingMixin.__init__(self, logger)

        initial_state = self.config.get("initial_state")
        self.state = State[initial_state.upper()] if initial_state else State.STOPPED
        self.last_process = datetime(1970, 1, 1, tzinfo=timezone.utc)

    def cleanup(self) -> None:
        """
        Cleanup pending resources on an already stopped bot
        :return: None
        """
        logger.info("Cleaning up modules ...")

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
        if __group__ == "master":
            self.check_bots()
            self.refresh_strategies()
            self.check_strategies()
        self.last_process = datetime.now(timezone.utc)

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
            outdated = parse(bot.version) < parse(self.config["cg_version"])
            if (status not in ("Running", "Pending")) or outdated:
                if bot.is_strategy:
                    strategy = Strategy.strategy_by_bot_id(bot_id)
                    env = (
                        {
                            "COINGRO__STRATEGY": bot.bot_name,
                            "COINGRO__INITIAL_STATE": "running",
                            "COINGRO__MAX_OPEN_TRADES": "-1",
                            "COINGRO__DRY_RUN_WALLET": "100000",
                        }
                        if strategy
                        else {}
                    )
                    self.create_bot(bot_id, update=outdated, env_vars=env)
                else:
                    self.create_bot(bot_id, update=outdated)

    def create_bot(
        self,
        bot_id: Optional[str] = None,
        bot_name: Optional[str] = None,
        user: Optional[str] = None,
        is_strategy: bool = False,
        update: bool = False,
        env_vars: Dict[str, Any] = {},
    ) -> Tuple[str, str]:
        if not bot_id:
            uid = uuid.uuid4().hex
            bot_id = f"bot-{uid}"
            while Bot.bot_by_id(bot_id):
                uid = uuid.uuid4().hex
                bot_id = f"bot-{uid}"

        bot_id = bot_id.lower()

        bot = Bot.bot_by_id(bot_id)

        if not bot_name:
            if bot:
                bot_name = bot.bot_name
            else:
                bot_name = get_name(adj=BOT_NAME_ADJECTIVES, sep=" ").title()

        env_vars.update({"COINGRO__BOT_NAME": bot_name})

        if bot:
            env_vars.update({"COINGRO__INITIAL_STATE": bot.state.name.lower()})

        instance = self.k8s_client.get_coingro_instance(bot_id)
        # status = instance.status.phase if instance else None
        is_deleted = True if bot and bot.deleted_at else False

        # if instance:
        #     logger.info(f'Bot {bot_id} status: {status}')

        if not is_deleted:
            bot_config = (
                bot.configuration
                if bot and bot.configuration and isinstance(bot.configuration, dict)
                else self.default_bot_config.copy()
            )
            bot_config.update({"bot_name": bot_name})

            if instance:
                self.k8s_client.replace_coingro_instance(bot_id, bot_config, env_vars)
                logger.info(f"Restarted coingro instance {bot_id}.")
            else:
                self.k8s_client.create_coingro_instance(bot_id, bot_config, env_vars)
                logger.info(f"Created coingro instance {bot_id}.")

            if not bot:
                bot = Bot(bot_id=bot_id, bot_name=bot_name, user_id=user, is_strategy=is_strategy)

                if is_strategy:
                    bot.state = State["RUNNING"]
                    bot.strategy = bot_name
                    bot.exchange = self.config.get("default_strategy_exchange", DEFAULT_EXCHANGE)
                    bot.stake_currency = self.config.get(
                        "default_strategy_stake_currency", DEFAULT_STAKE_CURRENCY
                    )
                elif "cg_initial_state" in self.config:
                    bot.state = State[self.config["cg_initial_state"].upper()]

                Bot.query.session.add(bot)

            bot.configuration = bot_config
            bot.is_active = True
            bot.image = self.config["cg_image"]
            bot.version = self.config["cg_version"]
            bot.api_url = (
                f"http://{bot_id}/{self.config['cg_api_router_prefix']}"
                if "cg_api_router_prefix" in self.config
                else f"http://{bot_id}"
            )
            if update:
                bot.updated_at = datetime.utcnow()
            Bot.commit()

        return bot.bot_id, bot.bot_name  # type: ignore

    def deactivate_bot(self, bot_id: str, delete: bool = False) -> Optional[str]:
        bot = Bot.bot_by_id(bot_id)
        if bot:
            self.k8s_client.delete_coingro_instance(bot_id)
            logger.info(f"Deleted coingro instance {bot_id}.")

            bot.is_active = False
            if delete:
                bot.deleted_at = datetime.utcnow()
            Bot.commit()
        return bot.bot_id if bot else None

    def get_strategy_objects(self) -> List[Dict[str, Any]]:
        default_directory = "/coingro/strategies" if __env__ == "kubernetes" else "strategies"
        directory = Path(self.config.get("strategy_path", default_directory))
        return StrategyResolver.search_all_objects(
            directory, False, self.config.get("recursive_strategy_search", True)
        )

    def check_strategies(self) -> None:
        strategy_objects = self.get_strategy_objects()
        for obj in strategy_objects:
            name = obj["name"]
            strategy_class = obj["class"]
            env = {
                "COINGRO__STRATEGY": name,
                "COINGRO__INITIAL_STATE": "running",
                "COINGRO__MAX_OPEN_TRADES": "-1",
                "COINGRO__DRY_RUN_WALLET": "100000",
            }
            if name not in Strategy.strategy_names():
                bot_id, _ = self.create_bot(
                    bot_id=name, bot_name=name, is_strategy=True, env_vars=env
                )
                bot = Bot.bot_by_id(bot_id)
                strategy = Strategy(
                    bot_id=bot.id if bot else None,  # Should not be none
                    strategy_name=strategy_class.__strategy_name__
                    if strategy_class.__strategy_name__
                    else name,
                    category=strategy_class.__category__,
                    tags=",".join(strategy_class.__tags__),
                    short_description=strategy_class.__short_description__,
                    long_description=strategy_class.__long_description__,
                )
                Strategy.query.session.add(strategy)
                Strategy.commit()

        strategy_names = [obj["name"] for obj in strategy_objects]
        for strategy in Strategy.get_active_strategies():
            if strategy.bot.bot_name not in strategy_names:
                self.deactivate_bot(strategy.bot.bot_id)

    def refresh_strategies(self) -> None:
        for strategy in Strategy.get_active_strategies():
            if (not strategy.latest_refresh) or (
                datetime.utcnow() - strategy.latest_refresh > timedelta(hours=1)
            ):
                api_url = strategy.bot.api_url
                strategy.bot.strategy = strategy.bot.bot_name
                try:
                    data = self.coingro_client.profit(api_url)
                    strategy.profit_ratio_mean = data["profit_all_ratio_mean"]
                    strategy.profit_ratio_sum = data["profit_all_ratio_sum"]
                    strategy.profit_ratio = data["profit_all_ratio"]
                    strategy.first_trade = datetime.fromtimestamp(
                        data["first_trade_timestamp"] / 1000
                    )
                    strategy.latest_trade = datetime.fromtimestamp(
                        data["latest_trade_timestamp"] / 1000
                    )
                    strategy.avg_duration = pd.Timedelta(data["avg_duration"]).to_pytimedelta()
                    strategy.winning_trades = data["winning_trades"]
                    strategy.losing_trades = data["losing_trades"]
                    strategy.trade_count = strategy.winning_trades + strategy.losing_trades

                    data = self.coingro_client.trade_summary(api_url)
                    daily = data["daily"]
                    strategy.daily_profit = daily["data"][0]["rel_profit"]
                    strategy.daily_trade_count = daily["data"][0]["trade_count"]

                    weekly = data["weekly"]
                    strategy.weekly_profit = weekly["data"][0]["rel_profit"]
                    strategy.weekly_trade_count = weekly["data"][0]["trade_count"]

                    monthly = data["monthly"]
                    strategy.monthly_profit = monthly["data"][0]["rel_profit"]
                    strategy.monthly_trade_count = monthly["data"][0]["trade_count"]

                    strategy.latest_refresh = datetime.utcnow()

                    Strategy.commit()
                    logger.info(f"Updated trade statistics for strategy {strategy.bot.bot_name}.")
                except Exception as e:
                    logger.warning(
                        f"Could not update trade statistics for strategy "
                        f"{strategy.bot.bot_name} due to {repr(e)}."
                    )
