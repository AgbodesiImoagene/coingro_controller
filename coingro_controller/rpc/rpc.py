"""
This module contains class to define a RPC communications
"""
import logging
from typing import Any, Dict, Optional, Union

import psutil
from coingro.constants import DATETIME_PRINT_FORMAT
from coingro.exchange.common import SUPPORTED_EXCHANGES
from coingro.rpc import RPCException
from coingro.rpc.fiat_convert import CryptoToFiatConverter
from dateutil.tz import tzlocal

from coingro_controller.controller import Controller
from coingro_controller.persistence import Strategy
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
        self._controller: Controller = controller
        self._client: CoingroClient = controller.coingro_client
        self._config: Dict[str, Any] = controller.config

    @staticmethod
    def _rpc_list_strategies() -> Dict[str, Any]:
        return {'strategies': [strategy.to_json(True)
                               for strategy in Strategy.get_active_strategies()]}

    @staticmethod
    def _rpc_get_strategy(strategy_name: str) -> Dict[str, Any]:
        strategy = Strategy.strategy_by_name(strategy_name)
        if strategy:
            return strategy.to_json()
        else:
            raise RPCException(f'Could not find strategy {strategy_name}.')

    @staticmethod
    def _rpc_sysinfo() -> Dict[str, Any]:
        return {
            "cpu_pct": psutil.cpu_percent(interval=1, percpu=True),
            "ram_pct": psutil.virtual_memory().percent
        }

    def _health(self) -> Dict[str, Union[str, int]]:
        last_p = self._controller.last_process
        return {
            'last_process': str(last_p),
            'last_process_loc': last_p.astimezone(tzlocal()).strftime(DATETIME_PRINT_FORMAT),
            'last_process_ts': int(last_p.timestamp()),
        }

    def _state(self) -> Dict[str, str]:
        return {
            'state': str(self._controller.state),
        }

    @staticmethod
    def _rpc_exchange_info(exchange: str) -> Dict[str, Any]:
        exchange = exchange.lower()
        if exchange not in SUPPORTED_EXCHANGES:
            raise RPCException(f'{exchange} is not a supported exchange.')
        res = {}

        try:
            import ccxt
            exchange_class = getattr(ccxt, exchange)()

            res = {'name': exchange,
                   'required_credentials': exchange_class.requiredCredentials}
        except Exception as e:
            raise RPCException(str(e)) from e
        return res

    def _rpc_create_bot(self, user_id: str) -> Dict[str, Any]:
        try:
            bot_id = self._controller.create_bot(user=user_id)
            return {
                'bot_id': bot_id,
                'status': 'Successfully created coingro bot.',
            }
        except Exception as e:
            raise RPCException(f'Could not create bot due to {e}.')

    def _rpc_activate_bot(self, bot_id: str) -> Dict[str, Any]:
        try:
            _bot_id = self._controller.create_bot(name=bot_id)
            return {
                'bot_id': _bot_id,
                'status': 'Successfully activated coingro bot.',
            }
        except Exception as e:
            raise RPCException(f'Could not activate bot due to {e}.')

    def _rpc_deactivate_bot(self, bot_id: str) -> Dict[str, Any]:
        try:
            bot_id = self._controller.deactivate_bot(name=bot_id)
            return {
                'bot_id': bot_id,
                'status': 'Successfully deactivated coingro bot.',
            }
        except Exception as e:
            raise RPCException(f'Could not deactivate bot due to {e}.')

    def _rpc_delete_bot(self, bot_id: str) -> Dict[str, Any]:
        try:
            bot_id = self._controller.deactivate_bot(name=bot_id, delete=True)
            return {
                'bot_id': bot_id,
                'status': 'Successfully deleted coingro bot.',
            }
        except Exception as e:
            raise RPCException(f'Could not delete bot due to {e}.')
