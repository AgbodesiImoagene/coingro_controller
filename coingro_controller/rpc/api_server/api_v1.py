import logging
from copy import deepcopy
from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, Depends, Query
from fastapi.exceptions import HTTPException

from coingro.constants import SUPPORTED_FIAT, SUPPORTED_STAKE_CURRENCIES, USERPATH_STRATEGIES
from coingro.data.history import get_datahandler
from coingro.enums import CandleType, TradingMode
from coingro.exceptions import OperationalException
from coingro.exchange.common import SUPPORTED_EXCHANGES
from coingro.rpc import RPC
from coingro.rpc.api_server.api_schemas import (AvailablePairs, Balances, BlacklistPayload,
                                                BlacklistResponse, Count, Daily, DeleteLockRequest,
                                                DeleteTrade, ExchangeInfo, ForceEnterPayload,
                                                ForceEnterResponse, ForceExitPayload, Health, Locks,
                                                Logs, OpenTradeSchema, PairHistory,
                                                PerformanceEntry, Ping, PlotConfig, Profit,
                                                ResultMsg, SettingsOptions, ShowConfig, State,
                                                Stats, StatusMsg, StrategyListResponse,
                                                StrategyResponse, SysInfo, UpdateExchangePayload,
                                                UpdateSettingsPayload, UpdateStrategyPayload,
                                                Version, WhitelistResponse)
from coingro.rpc.rpc import RPCException

from coingro_controller import __version__
from coingro_controller.rpc.api_server.deps import (get_bot, get_client, get_config, get_rpc, 
                                                    get_rpc_optional, get_user)


logger = logging.getLogger(__name__)

# API version
# Pre-1.1, no version was provided
# Version increments should happen in "small" steps (1.1, 1.12, ...) unless big changes happen.
# 1.11: forcebuy and forcesell accept ordertype
# 1.12: add blacklist delete endpoint
# 1.13: forcebuy supports stake_amount
# versions 2.xx -> futures/short branch
# 2.14: Add entry/exit orders to trade response
# 2.15: Add backtest history endpoints
# 2.16: Additional daily metrics
# 3.1: Add config update endpoints
API_VERSION = 3.1

router = APIRouter()


@router.get('/ping', response_model=Ping)
def ping():
    """simple ping"""
    return {"status": "pong"}


@router.get('/version', response_model=Version, tags=['info'])
def version(bot=Depends(get_bot), client=Depends(get_client)):
    """ Version info"""
    try:
        return client.version(bot.bot_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=e)


@router.get('/controller_version', response_model=Version, tags=['controller', 'info'])
def controller_version():
    """ Version info"""
    return {"version": __version__}


@router.get('/balance', response_model=Balances, tags=['info'])
def balance(bot=Depends(get_bot), client=Depends(get_client)):
    """Account Balances"""
    try:
        return client.balance(bot.bot_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=e)


@router.get('/count', response_model=Count, tags=['info'])
def count(bot=Depends(get_bot), client=Depends(get_client)):
    try:
        return client.count(bot.bot_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=e)


@router.get('/performance', response_model=List[PerformanceEntry], tags=['info'])
def performance(bot=Depends(get_bot), client=Depends(get_client)):
    try:
        return client.performance(bot.bot_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=e)


@router.get('/profit', response_model=Profit, tags=['info'])
def profit(bot=Depends(get_bot), client=Depends(get_client)):
    try:
        return client.profit(bot.bot_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=e)


@router.get('/stats', response_model=Stats, tags=['info'])
def stats(bot=Depends(get_bot), client=Depends(get_client)):
    try:
        return client.stats(bot.bot_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=e)


@router.get('/daily', response_model=Daily, tags=['info'])
def daily(timescale: int = 7, bot=Depends(get_bot), client=Depends(get_client)):
    try:
        return client.daily(bot.bot_id, timescale)
    except Exception as e:
        raise HTTPException(status_code=500, detail=e)


@router.get('/status', response_model=List[OpenTradeSchema], tags=['info'])
def status(bot=Depends(get_bot), client=Depends(get_client)):
    try:
        return client.status(bot.bot_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=e)


# Using the responsemodel here will cause a ~100% increase in response time (from 1s to 2s)
# on big databases. Correct response model: response_model=TradeResponse,
@router.get('/trades', tags=['info', 'trading'])
def trades(limit: int = 500, offset: int = 0, bot=Depends(get_bot), client=Depends(get_client)):
    try:
        return client.trades(bot.bot_id, limit, offset)
    except Exception as e:
        raise HTTPException(status_code=500, detail=e)


@router.get('/trade/{tradeid}', response_model=OpenTradeSchema, tags=['info', 'trading'])
def trade(tradeid: int = 0, bot=Depends(get_bot), client=Depends(get_client)):
    try:
        return client.trade(bot.bot_id, tradeid)
    except Exception as e:
        raise HTTPException(status_code=500, detail=e)


@router.delete('/trades/{tradeid}', response_model=DeleteTrade, tags=['info', 'trading'])
def trades_delete(tradeid: int, bot=Depends(get_bot), client=Depends(get_client)):
    try:
        return client.delete_trade(bot.bot_id, tradeid)
    except Exception as e:
        raise HTTPException(status_code=500, detail=e)


# # TODO: Missing response model
# @router.get('/edge', tags=['info'])
# def edge(rpc: RPC = Depends(get_rpc)):
#     return rpc._rpc_edge()


@router.get('/show_config', response_model=ShowConfig, tags=['info'])
def show_config(bot=Depends(get_bot), client=Depends(get_client)):
    try:
        return client.show_config(bot.bot_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=e)


@router.post('/forceenter', response_model=ForceEnterResponse, tags=['trading'])
def force_entry(payload: ForceEnterPayload, bot=Depends(get_bot), client=Depends(get_client)):
    side = payload.side.value if payload.side else None
    ordertype = payload.ordertype.value if payload.ordertype else None

    try:
        return client.forceenter(bot.bot_id, payload.pair, side, payload.price, ordertype,
                                 payload.stake_amount, payload.entry_tag)
    except Exception as e:
       raise HTTPException(status_code=500, detail=e)


@router.post('/forceexit', response_model=ResultMsg, tags=['trading'])
def forceexit(payload: ForceExitPayload, bot=Depends(get_bot), client=Depends(get_client)):
    ordertype = payload.ordertype.value if payload.ordertype else None

    try:
        return client.forceexit(bot.bot_id, payload.tradeid, ordertype)
    except Exception as e:
        raise HTTPException(status_code=500, detail=e)


@router.get('/blacklist', response_model=BlacklistResponse, tags=['info', 'pairlist'])
def blacklist(bot=Depends(get_bot), client=Depends(get_client)):
    try:
        return client.blacklist(bot.bot_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=e)


@router.post('/blacklist', response_model=BlacklistResponse, tags=['info', 'pairlist'])
def blacklist_post(payload: BlacklistPayload, bot=Depends(get_bot), client=Depends(get_client)):
    try:
        return client.blacklist(bot.bot_id, *(payload.blacklist))
    except Exception as e:
        raise HTTPException(status_code=500, detail=e)


@router.delete('/blacklist', response_model=BlacklistResponse, tags=['info', 'pairlist'])
def blacklist_delete(pairs_to_delete: List[str] = Query([]), bot=Depends(get_bot), client=Depends(get_client)):
    """Provide a list of pairs to delete from the blacklist"""
    try:
        return client.delete_blacklist(bot.bot_id, pairs_to_delete)
    except Exception as e:
        raise HTTPException(status_code=500, detail=e)


@router.get('/whitelist', response_model=WhitelistResponse, tags=['info', 'pairlist'])
def whitelist(bot=Depends(get_bot), client=Depends(get_client)):
    try:
        return client.whitelist(bot.bot_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=e)


@router.get('/locks', response_model=Locks, tags=['info', 'locks'])
def locks(bot=Depends(get_bot), client=Depends(get_client)):
    try:
        return client.locks(bot.bot_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=e)


@router.delete('/locks/{lockid}', response_model=Locks, tags=['info', 'locks'])
def delete_lock(lockid: int, bot=Depends(get_bot), client=Depends(get_client)):
    try:
        return client.delete_lock(bot.bot_id, lockid)
    except Exception as e:
        raise HTTPException(status_code=500, detail=e)


@router.post('/locks/delete', response_model=Locks, tags=['info', 'locks'])
def delete_lock_pair(payload: DeleteLockRequest, bot=Depends(get_bot), client=Depends(get_client)):
    try:
        return client.delete_lock(bot.bot_id, payload.lockid, payload.pair)
    except Exception as e:
        raise HTTPException(status_code=500, detail=e)


@router.get('/logs', response_model=Logs, tags=['info'])
def logs(limit: Optional[int] = None, bot=Depends(get_bot), client=Depends(get_client)):
    try:
        return client.logs(bot.bot_id, limit)
    except Exception as e:
        raise HTTPException(status_code=500, detail=e)


@router.post('/start', response_model=StatusMsg, tags=['bot control'])
def start(bot=Depends(get_bot), client=Depends(get_client)):
    try:
        return client.start(bot.bot_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=e)


@router.post('/stop', response_model=StatusMsg, tags=['bot control'])
def stop(bot=Depends(get_bot), client=Depends(get_client)):
    try:
        return client.stop(bot.bot_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=e)


@router.post('/stopbuy', response_model=StatusMsg, tags=['bot control'])
def stop_buy(bot=Depends(get_bot), client=Depends(get_client)):
    try:
        return client.stopbuy(bot.bot_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=e)


@router.post('/reload_config', response_model=StatusMsg, tags=['bot control'])
def reload_config(bot=Depends(get_bot), client=Depends(get_client)):
    try:
        return client.reload_config(bot.bot_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=e)


# @router.get('/pair_candles', response_model=PairHistory, tags=['candle data'])
# def pair_candles(
#         pair: str, timeframe: str, limit: Optional[int] = None, rpc: RPC = Depends(get_rpc)):
#     return rpc._rpc_analysed_dataframe(pair, timeframe, limit)


# @router.get('/pair_history', response_model=PairHistory, tags=['candle data'])
# def pair_history(pair: str, timeframe: str, timerange: str, strategy: str,
#                  config=Depends(get_config), exchange=Depends(get_exchange)):
#     # The initial call to this endpoint can be slow, as it may need to initialize
#     # the exchange class.
#     config = deepcopy(config)
#     config.update({
#         'strategy': strategy,
#     })
#     return RPC._rpc_analysed_history_full(config, pair, timeframe, timerange, exchange)


# @router.get('/plot_config', response_model=PlotConfig, tags=['candle data'])
# def plot_config(rpc: RPC = Depends(get_rpc)):
#     return PlotConfig.parse_obj(rpc._rpc_plot_config())


# change response models of the following two
@router.get('/strategies')  # , response_model=StrategyListResponse, tags=['strategy'])
def list_strategies():
    return RPC._rpc_list_strategies()


@router.get('/strategy/{strategy}')  # , response_model=StrategyResponse, tags=['strategy'])
def get_strategy(strategy: str):
    return RPC._rpc_get_strategy()


# @router.get('/available_pairs', response_model=AvailablePairs, tags=['candle data'])
# def list_available_pairs(timeframe: Optional[str] = None, stake_currency: Optional[str] = None,
#                          candletype: Optional[CandleType] = None, config=Depends(get_config)):

#     dh = get_datahandler(config['datadir'], config.get('dataformat_ohlcv'))
#     trading_mode: TradingMode = config.get('trading_mode', TradingMode.SPOT)
#     pair_interval = dh.ohlcv_get_available_data(config['datadir'], trading_mode)

#     if timeframe:
#         pair_interval = [pair for pair in pair_interval if pair[1] == timeframe]
#     if stake_currency:
#         pair_interval = [pair for pair in pair_interval if pair[0].endswith(stake_currency)]
#     if candletype:
#         pair_interval = [pair for pair in pair_interval if pair[2] == candletype]
#     else:
#         candle_type = CandleType.get_default(trading_mode)
#         pair_interval = [pair for pair in pair_interval if pair[2] == candle_type]

#     pair_interval = sorted(pair_interval, key=lambda x: x[0])

#     pairs = list({x[0] for x in pair_interval})
#     pairs.sort()
#     result = {
#         'length': len(pairs),
#         'pairs': pairs,
#         'pair_interval': pair_interval,
#     }
#     return result


@router.get('/sysinfo', response_model=SysInfo, tags=['info'])
def sysinfo(bot=Depends(get_bot), client=Depends(get_client)):
    try:
        return client.sysinfo(bot.bot_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=e)


@router.get('/health', response_model=Health, tags=['info'])
def health(bot=Depends(get_bot), client=Depends(get_client)):
    try:
        return client.health(bot.bot_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=e)


@router.get('/state', response_model=State, tags=['info'])
def state(bot=Depends(get_bot), client=Depends(get_client)):
    try:
        return client.state(bot.bot_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=e)


@router.get('/controller_sysinfo', response_model=SysInfo, tags=['info'])
def controller_sysinfo():
    return RPC._rpc_sysinfo()


@router.get('/controller_health', response_model=Health, tags=['info'])
def controller_health(rpc: RPC = Depends(get_rpc)):
    return rpc._health()


@router.get('/controller_state', response_model=State, tags=['info'])
def controller_state(rpc: RPC = Depends(get_rpc)):
    return rpc._state()


@router.get('/exchange/{exchange_name}', response_model=ExchangeInfo, tags=['info'])
def exchange_info(exchange_name: str):
    return RPC._rpc_exchange_info(exchange_name)


@router.get('/settings_options', response_model=SettingsOptions, tags=['info'])
def list_exchanges():
    return {
        'exchanges': SUPPORTED_EXCHANGES,
        'stake_currencies': SUPPORTED_STAKE_CURRENCIES,
        'fiat_display_currencies': SUPPORTED_FIAT
    }


@router.post('/exchange', response_model=StatusMsg, tags=['bot control', 'setup'])
def update_exchange(payload: UpdateExchangePayload,
                    bot=Depends(get_bot),
                    client=Depends(get_client)):
    kwargs = payload.dict(exclude_none=True)
    try:
        return client.update_exchange(bot.bot_id, **kwargs)
    except Exception as e:
        raise HTTPException(status_code=500, detail=e)


@router.post('/strategy', response_model=StatusMsg, tags=['bot control', 'setup'])
def update_strategy(payload: UpdateStrategyPayload,
                    bot=Depends(get_bot),
                    client=Depends(get_client)):
    kwargs = payload.dict(exclude_none=True)
    try:
        return client.update_strategy(bot.bot_id, **kwargs)
    except Exception as e:
        raise HTTPException(status_code=500, detail=e)


@router.post('/settings', response_model=StatusMsg, tags=['bot control', 'setup'])
def update_general_settings(payload: UpdateSettingsPayload,
                            bot=Depends(get_bot),
                            client=Depends(get_client)):
    kwargs = payload.dict(exclude_none=True)
    try:
        return client.update_settings(bot.bot_id, **kwargs)
    except Exception as e:
        raise HTTPException(status_code=500, detail=e)


@router.post('/reset_original_config', response_model=StatusMsg, tags=['bot control'])
def reset_original_config(bot=Depends(get_bot), client=Depends(get_client)):
    try:
        return client.reset_original_config(bot.bot_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=e)


@router.post('/create_bot', tags=['bot control'])
def create_bot(user=Depends(get_user), rpc=Depends(get_rpc)):
    return rpc._create_bot(user.id)


@router.post('/activate_bot', response_model=StatusMsg, tags=['bot control'])
def activate_bot(bot=Depends(get_bot), rpc=Depends(get_rpc)):
    return rpc._activate_bot(bot.id)


@router.post('/deactivate_bot', response_model=StatusMsg, tags=['bot control'])
def deactivate_bot(bot=Depends(get_bot), rpc=Depends(get_rpc)):
    return rpc._deactivate_bot(bot.id)


@router.post('/delete_bot', response_model=StatusMsg, tags=['bot control'])
def delete_bot(bot=Depends(get_bot), rpc=Depends(get_rpc)):
    return rpc._delete_bot(bot.id)
