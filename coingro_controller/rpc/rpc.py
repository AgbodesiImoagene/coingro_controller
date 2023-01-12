"""
This module contains class to define a RPC communications
"""
import logging
from typing import Any, Dict, Optional, Union

import psutil
from dateutil.tz import tzlocal

from coingro.constants import DATETIME_PRINT_FORMAT
from coingro.exchange.common import SUPPORTED_EXCHANGES
from coingro.rpc import RPCException
from coingro.rpc.fiat_convert import CryptoToFiatConverter
from coingro_controller.persistence import Bot, Strategy
from coingro_controller.rpc.client import CoingroClient

logger = logging.getLogger(__name__)


class RPC:
    """
    RPC class can be used to have extra feature, like bot data, and access to DB data
    """

    # Bind _fiat_converter if needed
    _fiat_converter: Optional[CryptoToFiatConverter] = None

    def __init__(self, controller) -> None:
        """
        Initializes all enabled rpc modules
        :param coingro: Instance of a coingro controller
        :return: None
        """
        self._controller = controller
        self._client: CoingroClient = controller.coingro_client
        self._config: Dict[str, Any] = controller.config
        self._bot_config: Dict[str, Any] = controller.default_bot_config

    @staticmethod
    def _rpc_list_strategies() -> Dict[str, Any]:
        return {
            "strategies": [strategy.to_json(True) for strategy in Strategy.get_active_strategies()]
        }

    @staticmethod
    def _rpc_get_strategy(strategy_name: str) -> Dict[str, Any]:
        strategy = Strategy.strategy_by_name(strategy_name)
        if strategy:
            return strategy.to_json()
        else:
            raise RPCException(f"Could not find strategy {strategy_name}.")

    @staticmethod
    def _rpc_sysinfo() -> Dict[str, Any]:
        return {
            "cpu_pct": psutil.cpu_percent(interval=1, percpu=True),
            "ram_pct": psutil.virtual_memory().percent,
        }

    def _health(self) -> Dict[str, Union[str, int]]:
        last_p = self._controller.last_process
        return {
            "last_process": str(last_p),
            "last_process_loc": last_p.astimezone(tzlocal()).strftime(DATETIME_PRINT_FORMAT),
            "last_process_ts": int(last_p.timestamp()),
        }

    @staticmethod
    def _rpc_exchange_info() -> Dict[str, Dict[str, Any]]:
        res = {}

        try:
            import ccxt

            for exchange in SUPPORTED_EXCHANGES:
                exchange_class = getattr(ccxt, exchange)()

                res[exchange] = {"required_credentials": exchange_class.requiredCredentials}

            return res
        except Exception as e:
            raise RPCException(str(e)) from e

    def _rpc_create_bot(self, user_id: int) -> Dict[str, Any]:
        try:
            bot_id, bot_name = self._controller.create_bot(user=user_id)
            return {
                "bot_id": bot_id,
                "bot_name": bot_name,
                "status": "Successfully created coingro bot.",
            }
        except Exception as e:
            raise RPCException(f"Could not create bot due to {e}.")

    def _rpc_activate_bot(self, bot_id: str) -> Dict[str, Any]:
        try:
            _ = self._controller.create_bot(bot_id=bot_id)
            return {
                "status": "Successfully activated coingro bot.",
            }
        except Exception as e:
            raise RPCException(f"Could not activate bot due to {e}.")

    def _rpc_deactivate_bot(self, bot_id: str) -> Dict[str, Any]:
        try:
            _ = self._controller.deactivate_bot(bot_id=bot_id)
            return {
                "status": "Successfully deactivated coingro bot.",
            }
        except Exception as e:
            raise RPCException(f"Could not deactivate bot due to {e}.")

    def _rpc_delete_bot(self, bot_id: str) -> Dict[str, Any]:
        try:
            _ = self._controller.deactivate_bot(bot_id=bot_id, delete=True)
            return {
                "status": "Successfully deleted coingro bot.",
            }
        except Exception as e:
            raise RPCException(f"Could not delete bot due to {e}.")

    def _rpc_summary(self, bot_id: str) -> Dict[str, Any]:
        try:
            bot = Bot.bot_by_id(bot_id)
            url = bot.api_url if bot else ""
            timeunits = {"days": "daily", "weeks": "weekly", "months": "monthly"}
            resp = {}
            for unit in timeunits:
                timeframe = timeunits[unit]
                data = self._client.timeunit_profit(url, unit, 1)
                resp[timeframe] = data
            return resp
        except Exception as e:
            raise RPCException(str(e)) from e
