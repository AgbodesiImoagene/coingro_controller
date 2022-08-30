from datetime import datetime
from typing import Dict, List, Optional

from coingro.rpc.api_server.api_schemas import Daily, StatusMsg
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
    bot_name: str


class SummaryResponse(BaseModel):
    daily: Daily
    weekly: Daily
    monthly: Daily


class RequiredCredentials(BaseModel):
    apiKey: bool
    secret: bool
    uid: bool
    login: bool
    password: bool
    twofa: bool
    privateKey: bool
    walletAddress: bool
    token: bool


class ExchangeOptions(BaseModel):
    required_credentials: RequiredCredentials


class SettingsOptions(BaseModel):
    exchanges: Dict[str, ExchangeOptions]
    stake_currencies: List[str]
    forceenter_quote_currencies: List[str]
    fiat_display_currencies: List[str]
