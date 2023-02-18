import asyncio
import logging
from copy import deepcopy
from typing import List, Optional

from fastapi import APIRouter, Depends, Query
from fastapi.exceptions import HTTPException
from pydantic import ValidationError

from coingro.configuration.config_security import Encryption
from coingro.constants import (
    SUPPORTED_FIAT,
    SUPPORTED_FORCEENTER_CURRENCIES,
    SUPPORTED_STAKE_CURRENCIES,
)
from coingro.enums import State as StateEnum
from coingro.enums import TimeUnit
from coingro.rpc import RPC as Bot_RPC
from coingro.rpc.api_server.api_schemas import (
    Balances,
    BlacklistPayload,
    BlacklistResponse,
    Count,
    Daily,
    DeleteLockRequest,
    DeleteTrade,
    ForceEnterPayload,
    ForceEnterResponse,
    ForceExitPayload,
    Health,
    Locks,
    Logs,
    OpenTradeSchema,
    PerformanceEntry,
    Ping,
    Profit,
    ResultMsg,
    ShowConfig,
    State,
    Stats,
    StatusMsg,
    SysInfo,
    TimeUnitProfit,
    UpdateExchangePayload,
    UpdateSettingsPayload,
    UpdateStrategyPayload,
    Version,
    WhitelistResponse,
)
from coingro_controller import __version__
from coingro_controller.persistence import Bot
from coingro_controller.rpc import RPC
from coingro_controller.rpc.api_server.api_schemas import (
    BotStatus,
    SettingsOptions,
    StrategyListResponse,
    StrategyResponse,
    SummaryResponse,
)
from coingro_controller.rpc.api_server.deps import (
    get_bot,
    get_bot_config,
    get_client,
    get_rpc,
    get_user,
)

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


def validate_result(validator_class):  # noqa: C901
    def decorator(func):
        async def async_wrapper(*args, **kwargs):
            try:
                res = await func(*args, **kwargs)
                if isinstance(res, list):
                    for entry in res:
                        validator_class.validate(entry)
                else:
                    validator_class.validate(res)
                return res
            except ValidationError:
                if hasattr(res, "__getitem__") and "detail" in res:
                    raise HTTPException(status_code=400, detail=res["detail"])
                else:
                    raise HTTPException(status_code=400, detail=res)

        def sync_wrapper(*args, **kwargs):
            try:
                res = func(*args, **kwargs)
                if isinstance(res, list):
                    for entry in res:
                        validator_class.validate(entry)
                else:
                    validator_class.validate(res)
                return res
            except ValidationError:
                if hasattr(res, "__getitem__") and "detail" in res:
                    raise HTTPException(status_code=400, detail=res["detail"])
                else:
                    raise HTTPException(status_code=400, detail=res)

        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper

    return decorator


@router.get("/ping", response_model=Ping)
def ping():
    """simple ping"""
    return {"status": "pong"}


@router.get("/version", response_model=Version, tags=["info"])
@validate_result(Version)
def version(bot=Depends(get_bot), client=Depends(get_client)):
    """Version info"""
    return client.version(bot.api_url)


@router.get("/controller_version", response_model=Version, tags=["controller", "info"])
def controller_version():
    """Version info"""
    return {"version": __version__}


@router.get("/balance", response_model=Balances, tags=["info"])
@validate_result(Balances)
def balance(bot=Depends(get_bot), client=Depends(get_client)):
    """Account Balances"""
    return client.balance(bot.api_url)


@router.get("/count", response_model=Count, tags=["info"])
@validate_result(Count)
def count(bot=Depends(get_bot), client=Depends(get_client)):
    return client.count(bot.api_url)


@router.get("/performance", response_model=List[PerformanceEntry], tags=["info"])
@validate_result(PerformanceEntry)
def performance(bot=Depends(get_bot), client=Depends(get_client)):
    return client.performance(bot.api_url)


@router.get("/profit", response_model=Profit, tags=["info"])
@validate_result(Profit)
def profit(bot=Depends(get_bot), client=Depends(get_client)):
    res = client.profit(bot.api_url)
    if not res.get("profit_factor"):
        res["profit_factor"] = float("inf")
    return res


@router.get("/stats", response_model=Stats, tags=["info"])
@validate_result(Stats)
def stats(bot=Depends(get_bot), client=Depends(get_client)):
    return client.stats(bot.api_url)


@router.get("/daily", response_model=Daily, tags=["info"])
@validate_result(Daily)
def daily(timescale: int = 7, bot=Depends(get_bot), client=Depends(get_client)):
    return client.daily(bot.api_url, timescale)


@router.get("/status", response_model=List[OpenTradeSchema], tags=["info"])
@validate_result(OpenTradeSchema)
def status(bot=Depends(get_bot), client=Depends(get_client)):
    return client.status(bot.api_url)


# Using the responsemodel here will cause a ~100% increase in response time (from 1s to 2s)
# on big databases. Correct response model: response_model=TradeResponse,
@router.get("/trades", tags=["info", "trading"])
def trades(limit: int = 500, offset: int = 0, bot=Depends(get_bot), client=Depends(get_client)):
    return client.trades(bot.api_url, limit, offset)


@router.get("/trade/{tradeid}", response_model=OpenTradeSchema, tags=["info", "trading"])
@validate_result(OpenTradeSchema)
def trade(tradeid: int = 0, bot=Depends(get_bot), client=Depends(get_client)):
    return client.trade(bot.api_url, tradeid)


@router.delete("/trades/{tradeid}", response_model=DeleteTrade, tags=["info", "trading"])
@validate_result(DeleteTrade)
def trades_delete(tradeid: int, bot=Depends(get_bot), client=Depends(get_client)):
    return client.delete_trade(bot.api_url, tradeid)


# # TODO: Missing response model
# @router.get('/edge', tags=['info'])
# def edge(rpc: RPC = Depends(get_rpc)):
#     return rpc._rpc_edge()


@router.get("/show_config", response_model=ShowConfig, tags=["info"])
@validate_result(ShowConfig)
def show_config(bot=Depends(get_bot), client=Depends(get_client)):
    return client.show_config(bot.api_url)


@router.post("/forceenter", response_model=ForceEnterResponse, tags=["trading"])
@validate_result(ForceEnterResponse)
def forceentry(payload: ForceEnterPayload, bot=Depends(get_bot), client=Depends(get_client)):
    kwargs = payload.dict(exclude_none=True)
    return client.forceenter(bot.api_url, **kwargs)


@router.post("/forceexit", response_model=ResultMsg, tags=["trading"])
@validate_result(ResultMsg)
def forceexit(payload: ForceExitPayload, bot=Depends(get_bot), client=Depends(get_client)):
    kwargs = payload.dict(exclude_none=True)
    return client.forceexit(bot.api_url, **kwargs)


@router.get("/blacklist", response_model=BlacklistResponse, tags=["info", "pairlist"])
@validate_result(BlacklistResponse)
def blacklist(bot=Depends(get_bot), client=Depends(get_client)):
    return client.blacklist(bot.api_url)


@router.post("/blacklist", response_model=BlacklistResponse, tags=["info", "pairlist"])
@validate_result(BlacklistResponse)
def blacklist_post(payload: BlacklistPayload, bot=Depends(get_bot), client=Depends(get_client)):
    return client.blacklist(bot.api_url, *(payload.blacklist))


@router.delete("/blacklist", response_model=BlacklistResponse, tags=["info", "pairlist"])
@validate_result(BlacklistResponse)
def blacklist_delete(
    pairs_to_delete: List[str] = Query([]), bot=Depends(get_bot), client=Depends(get_client)
):
    """Provide a list of pairs to delete from the blacklist"""
    return client.delete_blacklist(bot.api_url, pairs_to_delete)


@router.get("/whitelist", response_model=WhitelistResponse, tags=["info", "pairlist"])
@validate_result(WhitelistResponse)
def whitelist(bot=Depends(get_bot), client=Depends(get_client)):
    return client.whitelist(bot.api_url)


@router.get("/locks", response_model=Locks, tags=["info", "locks"])
@validate_result(Locks)
def locks(bot=Depends(get_bot), client=Depends(get_client)):
    return client.locks(bot.api_url)


@router.delete("/locks/{lockid}", response_model=Locks, tags=["info", "locks"])
@validate_result(Locks)
def delete_lock(lockid: int, bot=Depends(get_bot), client=Depends(get_client)):
    return client.delete_lock(bot.api_url, lockid)


@router.post("/locks/delete", response_model=Locks, tags=["info", "locks"])
@validate_result(Locks)
def delete_lock_pair(payload: DeleteLockRequest, bot=Depends(get_bot), client=Depends(get_client)):
    return client.delete_lock(bot.api_url, payload.lockid, payload.pair)


@router.get("/logs", response_model=Logs, tags=["info"])
@validate_result(Logs)
def logs(limit: Optional[int] = None, bot=Depends(get_bot), client=Depends(get_client)):
    return client.logs(bot.api_url, limit)


@router.post("/start", response_model=StatusMsg, tags=["bot control"])
def start(bot=Depends(get_bot), client=Depends(get_client)):
    try:
        res = client.start(bot.api_url)
        StatusMsg(**res)
        bot.state = StateEnum.RUNNING
        Bot.commit()
        return res
    except ValidationError:
        if hasattr(res, "__getitem__") and "detail" in res:
            raise HTTPException(status_code=400, detail=res["detail"])
        else:
            raise HTTPException(status_code=400, detail=res)
    except Exception as e:
        raise HTTPException(status_code=500, detail=e)


@router.post("/stop", response_model=StatusMsg, tags=["bot control"])
def stop(bot=Depends(get_bot), client=Depends(get_client)):
    try:
        res = client.stop(bot.api_url)
        StatusMsg(**res)
        bot.state = StateEnum.STOPPED
        Bot.commit()
        return res
    except ValidationError:
        if hasattr(res, "__getitem__") and "detail" in res:
            raise HTTPException(status_code=400, detail=res["detail"])
        else:
            raise HTTPException(status_code=400, detail=res)
    except Exception as e:
        raise HTTPException(status_code=500, detail=e)


@router.post("/stopbuy", response_model=StatusMsg, tags=["bot control"])
@validate_result(StatusMsg)
def stop_buy(bot=Depends(get_bot), client=Depends(get_client)):
    return client.stopbuy(bot.api_url)


@router.post("/reload_config", response_model=StatusMsg, tags=["bot control"])
@validate_result(StatusMsg)
def reload_config(bot=Depends(get_bot), client=Depends(get_client)):
    return client.reload_config(bot.api_url)


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
@router.get("/strategies", response_model=StrategyListResponse, tags=["info", "strategy"])
def list_strategies():
    return RPC._rpc_list_strategies()


@router.get("/strategy/{strategy}", response_model=StrategyResponse, tags=["info", "strategy"])
def get_strategy(strategy: str):
    return RPC._rpc_get_strategy(strategy)


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


@router.get("/sysinfo", response_model=SysInfo, tags=["info"])
@validate_result(SysInfo)
def sysinfo(bot=Depends(get_bot), client=Depends(get_client)):
    return client.sysinfo(bot.api_url)


@router.get("/health", response_model=Health, tags=["info"])
@validate_result(Health)
def health(bot=Depends(get_bot), client=Depends(get_client)):
    return client.health(bot.api_url)


@router.get("/state", response_model=State, tags=["info"])
@validate_result(State)
def state(bot=Depends(get_bot), client=Depends(get_client)):
    return client.state(bot.api_url)


@router.get("/controller_sysinfo", response_model=SysInfo, tags=["info"])
def controller_sysinfo():
    return RPC._rpc_sysinfo()


@router.get("/controller_health", response_model=Health, tags=["info"])
def controller_health(rpc=Depends(get_rpc)):
    return rpc._health()


# @router.get('/exchange/{exchange_name}', response_model=ExchangeInfo, tags=['info'])
# def exchange_info(exchange_name: str):
#     return RPC._rpc_exchange_info(exchange_name)


@router.get("/settings_options", response_model=SettingsOptions, tags=["info"])
def list_exchanges():
    return {
        "exchanges": RPC._rpc_exchange_info(),
        "stake_currencies": SUPPORTED_STAKE_CURRENCIES,
        "forceenter_quote_currencies": SUPPORTED_FORCEENTER_CURRENCIES,
        "fiat_display_currencies": SUPPORTED_FIAT,
    }


@router.post("/exchange", response_model=StatusMsg, tags=["bot control", "setup"])
def update_exchange(
    payload: UpdateExchangePayload, bot=Depends(get_bot), client=Depends(get_client)
):
    kwargs = payload.dict(exclude_none=True)
    try:
        res = client.update_exchange(bot.api_url, **kwargs)
        StatusMsg(**res)
        config = Bot_RPC._update_exchange(bot.configuration, kwargs)
        bot.configuration = deepcopy(config)
        if "name" in kwargs:
            bot.exchange = kwargs["name"]
            Bot.commit()
        return res
    except ValidationError:
        if hasattr(res, "__getitem__") and "detail" in res:
            raise HTTPException(status_code=400, detail=res["detail"])
        else:
            raise HTTPException(status_code=400, detail=res)


@router.post("/strategy", response_model=StatusMsg, tags=["bot control", "setup"])
def update_strategy(
    payload: UpdateStrategyPayload, bot=Depends(get_bot), client=Depends(get_client)
):
    kwargs = payload.dict(exclude_none=True)
    try:
        res = client.update_strategy(bot.api_url, **kwargs)
        StatusMsg(**res)
        config = Bot_RPC._update_strategy(bot.configuration, kwargs)
        bot.configuration = deepcopy(config)
        if "strategy" in kwargs:
            bot.strategy = kwargs["strategy"]
            Bot.commit()
        return res
    except ValidationError:
        if hasattr(res, "__getitem__") and "detail" in res:
            raise HTTPException(status_code=400, detail=res["detail"])
        else:
            raise HTTPException(status_code=400, detail=res)


@router.post("/settings", response_model=StatusMsg, tags=["bot control", "setup"])
def update_general_settings(
    payload: UpdateSettingsPayload, bot=Depends(get_bot), client=Depends(get_client)
):
    kwargs = payload.dict(exclude_none=True)
    try:
        res = client.update_settings(bot.api_url, **kwargs)
        StatusMsg(**res)
        config = Bot_RPC._update_general_settings(bot.configuration, kwargs)
        config = Encryption(config, bot.bot_id).get_encrypted_config()
        bot.configuration = deepcopy(config)
        if "bot_name" in kwargs:
            bot.bot_name = kwargs["bot_name"]
        if "stake_currency" in kwargs:
            bot.stake_currency = kwargs["stake_currency"]
        Bot.commit()
        return res
    except ValidationError:
        if hasattr(res, "__getitem__") and "detail" in res:
            raise HTTPException(status_code=400, detail=res["detail"])
        else:
            raise HTTPException(status_code=400, detail=res)


@router.post("/reset_original_config", response_model=StatusMsg, tags=["bot control"])
def reset_original_config(
    bot=Depends(get_bot), default_config=Depends(get_bot_config), client=Depends(get_client)
):
    try:
        res = client.reset_original_config(bot.api_url)
        StatusMsg(**res)
        bot.configuration = deepcopy(default_config)
        Bot.commit()
        return res
    except ValidationError:
        if hasattr(res, "__getitem__") and "detail" in res:
            raise HTTPException(status_code=400, detail=res["detail"])
        else:
            raise HTTPException(status_code=400, detail=res)


@router.post("/create_bot", response_model=BotStatus, tags=["bot control"])
def create_bot(user=Depends(get_user), rpc=Depends(get_rpc)):
    return rpc._rpc_create_bot(user.id)


@router.post("/activate_bot", response_model=StatusMsg, tags=["bot control"])
def activate_bot(bot=Depends(get_bot), rpc=Depends(get_rpc)):
    return rpc._rpc_activate_bot(bot.bot_id)


@router.post("/deactivate_bot", response_model=StatusMsg, tags=["bot control"])
def deactivate_bot(bot=Depends(get_bot), rpc=Depends(get_rpc)):
    return rpc._rpc_deactivate_bot(bot.bot_id)


@router.post("/delete_bot", response_model=StatusMsg, tags=["bot control"])
def delete_bot(bot=Depends(get_bot), rpc=Depends(get_rpc)):
    return rpc._rpc_delete_bot(bot.bot_id)


@router.get("/timeunit_profit", response_model=TimeUnitProfit, tags=["info"])
@validate_result(TimeUnitProfit)
def timeunit_profit(
    timeunit: TimeUnit, timescale: int = 1, bot=Depends(get_bot), client=Depends(get_client)
):
    timeframe = timeunit.value
    return client.timeunit_profit(bot.api_url, timeframe, timescale)


@router.get("/summary", response_model=SummaryResponse, tags=["info"])
@validate_result(SummaryResponse)
def summary(bot=Depends(get_bot), client=Depends(get_client)):
    return client.trade_summary(bot.api_url)
