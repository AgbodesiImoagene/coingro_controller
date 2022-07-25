"""
This module contains class to define a RPC communications
"""
import logging
from abc import abstractmethod
from copy import deepcopy
from datetime import date, datetime, timedelta, timezone
from math import isnan
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

import arrow
import psutil
from dateutil.relativedelta import relativedelta
from dateutil.tz import tzlocal
from numpy import NAN, inf, int64, mean
from pandas import DataFrame, NaT

from coingro import __version__
from coingro.configuration import Configuration, validate_config_consistency
from coingro.configuration.check_exchange import check_exchange
from coingro.configuration.save_config import save_to_config_file
from coingro.configuration.timerange import TimeRange
from coingro.constants import (CANCEL_REASON, DATETIME_PRINT_FORMAT, DEFAULT_CONFIG_SAVE,
                               USERPATH_CONFIG)
from coingro.data.history import load_data
from coingro.data.metrics import calculate_max_drawdown
from coingro.enums import CandleType, ExitCheckTuple, ExitType, SignalDirection, State, TradingMode
from coingro.exceptions import ExchangeError, PricingError
from coingro.exchange import timeframe_to_minutes, timeframe_to_msecs
from coingro.exchange.common import SUPPORTED_EXCHANGES
from coingro.loggers import bufferHandler
from coingro.misc import decimals_per_coin, shorten_date
from coingro.persistence import PairLocks, Trade
from coingro.persistence.models import PairLock
from coingro.plugins.pairlist.pairlist_helpers import expand_pairlist
from coingro.resolvers import ExchangeResolver, StrategyResolver
from coingro.rpc.fiat_convert import CryptoToFiatConverter
from coingro.wallets import PositionWallet, Wallet
from coingro.rpc import RPCException, RPCHandler

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

    def __init__(self, coingro_controller) -> None:
        """
        Initializes all enabled rpc modules
        :param coingro: Instance of a coingro controller
        :return: None
        """
        self._coingro_controller: Controller = coingro_controller
        self._client: CoingroClient = coingro_controller.coingro_client
        self._config: Dict[str, Any] = coingro_controller.config

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
        last_p = self._coingro_controller.last_process
        return {
            'last_process': str(last_p),
            'last_process_loc': last_p.astimezone(tzlocal()).strftime(DATETIME_PRINT_FORMAT),
            'last_process_ts': int(last_p.timestamp()),
        }

    def _state(self) -> Dict[str, str]:
        return {
            'state': str(self._coingro_controller.state),
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

    def _rpc_create_bot(user_id: str) -> Dict[str, Any]:
        try:
            bot_id = self._coingro_controller.create_bot(user=user_id)
            return {
                'bot_id': bot_id,
                'status': 'Successfully created coingro bot.',
            }
        except Exception as e:
            raise RPCException(f'Could not create bot due to {e}.')

    def _rpc_activate_bot(bot_id: str) -> Dict[str, Any]:
        try:
            bot_id = self._coingro_controller.create_bot(name=bot_id)
            return {
                'bot_id': bot_id,
                'status': 'Successfully activated coingro bot.',
            }
        except Exception as e:
            raise RPCException(f'Could not activate bot due to {e}.')

    def _rpc_deactivate_bot(bot_id: str) -> Dict[str, Any]:
        try:
            bot_id = self._coingro_controller.deactivate_bot(name=bot_id)
            return {
                'bot_id': bot_id,
                'status': 'Successfully deactivated coingro bot.',
            }
        except Exception as e:
            raise RPCException(f'Could not deactivate bot due to {e}.')

    def _rpc_delete_bot(bot_id: str) -> Dict[str, Any]:
        try:
            bot_id = self._coingro_controller.deactivate_bot(name=bot_id, delete=True)
            return {
                'bot_id': bot_id,
                'status': 'Successfully deleted coingro bot.',
            }
        except Exception as e:
            raise RPCException(f'Could not delete bot due to {e}.')
