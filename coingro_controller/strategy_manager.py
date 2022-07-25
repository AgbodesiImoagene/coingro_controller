import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List

from coingro.constants import USERPATH_STRATEGIES
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
        directory = Path(self._config.get('strategy_path', USERPATH_STRATEGIES))
        return StrategyResolver.search_all_objects(
            directory, False, self._config.get('recursive_strategy_search', False))

    def create_strategies(self) -> None:
        strategy_objects = self.get_strategy_objects()
        for obj in strategy_objects:
            name = obj['name']
            strategy_class = obj['class']
            env = {'COINGRO__STRATEGY': name}
            bot_id = self._controller.create_bot(name=name, is_strategy=True, env_vars=env)
            bot = Bot.bot_by_id(bot_id)
            if name not in Strategy.strategy_names():
                strategy = Strategy(name=name,
                                    bot_id=bot.id if bot else name,
                                    category=strategy_class.__category__,
                                    tags=','.join(strategy_class.__tags__),
                                    short_description=strategy_class.__short_description__,
                                    long_description=strategy_class.__long_description__,
                                    category=strategy_class.__category__)
                Strategy.query.session.add(strategy)
                Strategy.commit()

    def refresh(self):
        for strategy in Strategy.all():
            if (not strategy.latest_refresh or datetime.utcnow() - strategy.latest_refresh >
                    timedelta(days=1)):
                name = strategy.name
                try:
                    data = self.client.profit(name)
                    strategy.profit_ratio_mean = data['profit_all_ratio_mean']
                    strategy.profit_ratio_sum = data['profit_all_ratio_sum']
                    strategy.profit_ratio = data['profit_all_ratio']
                    strategy.first_trade = \
                        datetime.fromtimestamp(data['first_trade_timestamp'] / 1000)
                    strategy.latest_trade = \
                        datetime.fromtimestamp(data['latest_trade_timestamp'] / 1000)
                    strategy.avg_duration = data['avg_duration']
                    strategy.winning_trades = data['winning_trades']
                    strategy.losing_trades = data['losing_trades']
                    strategy.trade_count = strategy.winning_trades + strategy.losing_trades

                    data = self.client.timeunit_profit(name, 'days')
                    strategy.daily_profit = data['data'][0]['rel_profit']
                    strategy.daily_trade_count = data['data'][0]['trade_count']

                    data = self.client.timeunit_profit(name, 'weeks')
                    strategy.weekly_profit = data['data'][0]['rel_profit']
                    strategy.weekly_trade_count = data['data'][0]['trade_count']

                    data = self.client.timeunit_profit(name, 'months')
                    strategy.monthly_profit = data['data'][0]['rel_profit']
                    strategy.monthly_trade_count = data['data'][0]['trade_count']

                    strategy.latest_refresh = datetime.utcnow()

                    strategy.commit()
                except Exception as e:
                    logger.warning(f"Could not refresh perfomance stats for {name} due to {e}")
