import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List

import pandas as pd
from coingro.resolvers import StrategyResolver

from coingro_controller.persistence import Bot, Strategy
from coingro_controller.rpc import CoingroClient


logger = logging.getLogger(__name__)


class StrategyManager:
    def __init__(self, controller) -> None:
        self._controller = controller
        self._config: Dict[str, Any] = controller.config
        self._client: CoingroClient = CoingroClient(self._config)
        self.create_strategies()

    def get_strategy_objects(self) -> List[Dict[str, Any]]:
        directory = Path(self._config.get('strategy_path', '/coingro/strategies'))
        return StrategyResolver.search_all_objects(
            directory, False, self._config.get('recursive_strategy_search', True))

    def create_strategies(self) -> None:
        strategy_objects = self.get_strategy_objects()
        for obj in strategy_objects:
            name = obj['name']
            strategy_class = obj['class']
            env = {
                'COINGRO__STRATEGY': name,
                'COINGRO__INITIAL_STATE': 'running'
            }
            if name not in Strategy.strategy_names():
                bot_id = self._controller.create_bot(name=name, is_strategy=True, env_vars=env)
                bot = Bot.bot_by_id(bot_id)
                strategy = Strategy(name=name,
                                    bot_id=bot.id if bot else None,  # Should not be none
                                    category=strategy_class.__category__,
                                    tags=','.join(strategy_class.__tags__),
                                    short_description=strategy_class.__short_description__,
                                    long_description=strategy_class.__long_description__)
                Strategy.query.session.add(strategy)
                Strategy.commit()

    def refresh(self):
        for strategy in Strategy.all():
            if (not strategy.latest_refresh) or \
                    (datetime.utcnow() - strategy.latest_refresh > timedelta(hours=1)):
                api_url = strategy.bot.api_url
                strategy.bot.strategy = strategy.name
                try:
                    self._client.ping(api_url)
                except Exception:
                    logger.warning(f"Could not connect to strategy {strategy.name} "
                                   "to update trade statistics.")
                else:
                    data = self._client.profit(api_url)
                    strategy.profit_ratio_mean = data['profit_all_ratio_mean']
                    strategy.profit_ratio_sum = data['profit_all_ratio_sum']
                    strategy.profit_ratio = data['profit_all_ratio']
                    strategy.first_trade = \
                        datetime.fromtimestamp(data['first_trade_timestamp'] / 1000)
                    strategy.latest_trade = \
                        datetime.fromtimestamp(data['latest_trade_timestamp'] / 1000)
                    strategy.avg_duration = pd.Timedelta(data['avg_duration']).to_pytimedelta()
                    strategy.winning_trades = data['winning_trades']
                    strategy.losing_trades = data['losing_trades']
                    strategy.trade_count = strategy.winning_trades + strategy.losing_trades

                    data = self._client.timeunit_profit(api_url, 'days')
                    strategy.daily_profit = data['data'][0]['rel_profit']
                    strategy.daily_trade_count = data['data'][0]['trade_count']

                    data = self._client.timeunit_profit(api_url, 'weeks')
                    strategy.weekly_profit = data['data'][0]['rel_profit']
                    strategy.weekly_trade_count = data['data'][0]['trade_count']

                    data = self._client.timeunit_profit(api_url, 'months')
                    strategy.monthly_profit = data['data'][0]['rel_profit']
                    strategy.monthly_trade_count = data['data'][0]['trade_count']

                    strategy.latest_refresh = datetime.utcnow()

                    strategy.commit()
                    logger.info(f"Updated trade statistics for strategy {strategy.name}.")
