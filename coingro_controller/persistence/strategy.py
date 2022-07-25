"""
This module contains the class to persist trades into SQLite
"""
import logging
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional

from sqlalchemy import (Boolean, Column, DateTime, Enum, Float, ForeignKey, BigInteger, Integer, String,
                        UniqueConstraint, Interval, Text, desc, func)
from sqlalchemy.orm import lazyload, relationship

from coingro.constants import DATETIME_PRINT_FORMAT
from coingro.enums import State

from coingro_controller.persistence.base import _DECL_BASE
from coingro_controller.persistence.bot import Bot


logger = logging.getLogger(__name__)


class Strategy(_DECL_BASE):
    """
    Strategy database model
    Keeps a record of coingro strategy bots and their performances
    """
    __tablename__ = 'strategies'

    id = Column(BigInteger, primary_key=True)
    name = Column(String(255), nullable=False, index=True, unique=True)
    bot_id = Column(String(255), ForeignKey('bots.id'), nullable=False, index=True, unique=True)
    bot = relationship("Bot", back_populates="strategies")

    # metadata
    category = Column(String(255))
    tags = Column(String(255))  # comma delimited list of tags
    short_description = Column(String(255))
    long_description = Column(Text)

    # perfomance
    daily_profit = Column(Float, default=0.0)
    daily_trade_count = Column(Integer, default=0)
    weekly_profit = Column(Float, default=0.0)
    weekly_trade_count = Column(Integer, default=0)
    monthly_profit = Column(Float, default=0.0)
    monthly_trade_count = Column(Integer, default=0)
    profit_ratio_mean = Column(Float, default=0.0)
    profit_ratio_sum = Column(Float, default=0.0)
    profit_ratio = Column(Float, default=0.0)
    trade_count = Column(Integer, default=0)
    first_trade_timestamp = Column(DateTime)
    latest_trade_timestamp = Column(DateTime)
    avg_duration = Column(Interval)
    winning_trades = Column(Integer)
    losing_trades = Column(Integer)

    latest_refresh = Column(DateTime)

    def __repr__(self):
        return (f'Strategy(id={self.id}, name={self.name}, bot_id={self.bot_id})')

    def to_json(self, minified: bool = False) -> Dict[str, Any]:
        resp = {
            'name': self.name,
            'bot_id': self.bot_id,
            'category': self.category,
            'tags': self.tags.split(','),
            'short_description': self.short_description,
            'daily_profit': self.daily_profit,
            'daily_trade_count': self.daily_trade_count,
            'weekly_profit': self.weekly_profit,
            'weekly_trade_count': self.weekly_trade_count,
            'monthly_profit': self.monthly_profit,
            'monthly_trade_count': self.monthly_trade_count,
            'latest_refresh': self.latest_refresh.strftime(DATETIME_PRINT_FORMAT) \
                if self.latest_refresh else None,
        }
        if not minified:
            resp.update({
                'long_description': self.long_description,
                'profit_ratio_mean': self.profit_ratio_mean,
                'profit_ratio_sum': self.profit_ratio_sum,
                'profit_ratio': self.profit_ratio,
                'trade_count': self.trade_count,
                'first_trade_timestamp': self.first_trade_timestamp.\
                    strftime(DATETIME_PRINT_FORMAT) if self.first_trade_timestamp else None,
                'latest_trade_timestamp': self.latest_trade_timestamp.\
                    strftime(DATETIME_PRINT_FORMAT) if self.latest_trade_timestamp else None,
                'avg_duration': self.avg_duration,
                'winning_trades': self.winning_trades,
                'losing_trades': self.losing_trades,
            })
        return resp

    @staticmethod
    def get_active_strategies() -> List['Strategy']:
        """
        Retrieve active strategies from the database
        :return: List of active strategies
        """
        return Strategy.query.join(Bot).filter(Bot.is_active.is_(True)).all()

    @staticmethod
    def strategy_by_name(name: str) -> Optional['Strategy']:
        """
        Retrieve strategy based on name
        :return: Strategy or None
        """
        return Strategy.query.filter(Strategy.name == name).first()

    @staticmethod
    def strategy_names() -> List[str]:
        """
        All strategy names
        :return: List of strategy names
        """
        return [strategy.name for strategy in Strategy.query.all()]

    @staticmethod
    def all() -> List[str]:
        """
        All strategies
        :return: List of strategies
        """
        return Strategy.query.all()

    @staticmethod
    def commit():
        Strategy.query.session.commit()
