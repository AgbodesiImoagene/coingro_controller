from datetime import datetime
from typing import List, Optional

from coingro.rpc.api_server.api_schemas import StatusMsg
from pydantic import BaseModel


class StrategyMini(BaseModel):
    name: str
    bot_id: int
    category: Optional[str]
    tags: Optional[List[str]]
    short_description: Optional[str]
    daily_profit: float
    daily_trade_count: int
    weekly_profit: float
    weekly_trade_count: int
    monthly_profit: float
    monthly_trade_count: int
    latest_refresh: Optional[str]


class StrategyResponse(StrategyMini):
    long_description: Optional[str]
    profit_ratio_mean: float
    profit_ratio_sum: float
    profit_ratio: float
    trade_count: Optional[int]
    first_trade: Optional[datetime]
    latest_trade: Optional[datetime]
    avg_duration: Optional[str]
    winning_trades: Optional[int]
    losing_trades: Optional[int]


class StrategyListResponse(BaseModel):
    strategies: List[StrategyMini]


class BotStatus(StatusMsg):
    bot_id: str
