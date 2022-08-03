"""
This module contains the class to persist trades into SQLite
"""
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from coingro.constants import DATETIME_PRINT_FORMAT
from coingro.enums import State
from sqlalchemy import BigInteger, Boolean, Column, DateTime, Enum, ForeignKey, String
from sqlalchemy.orm import relationship

from coingro_controller.persistence.base import _DECL_BASE


logger = logging.getLogger(__name__)


class Bot(_DECL_BASE):
    """
    Bot database model
    Keeps a record of all coingro instances active on the cluster
    """
    __tablename__ = 'bots'

    id = Column(BigInteger, primary_key=True)
    bot_id = Column(String(255), nullable=False, index=True, unique=True)
    user_id = Column(BigInteger, ForeignKey('users.id'), nullable=True, index=True)
    user = relationship("User", back_populates="bots")
    strategy_stats = relationship("Strategy", cascade="all, delete-orphan",
                                  lazy="joined", back_populates="bot")

    image = Column(String(255), nullable=False)
    version = Column(String(100), nullable=False)
    api_url = Column(String(255), nullable=False)
    strategy = Column(String(100), nullable=True)
    exchange = Column(String(25), nullable=True)
    state = Column(Enum(State), nullable=True)
    is_active = Column(Boolean, nullable=False, default=True, index=True)
    is_strategy = Column(Boolean, nullable=False, default=False, index=True)

    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime)
    deleted_at = Column(DateTime)

    @property
    def created_at_utc(self) -> datetime:
        """ Creation date with UTC timezoneinfo"""
        return self.created_at.replace(tzinfo=timezone.utc)

    @property
    def updated_at_utc(self) -> Optional[datetime]:
        """ Last update date with UTC timezoneinfo"""
        if self.updated_at:
            return self.updated_at.replace(tzinfo=timezone.utc)
        return None

    @property
    def deleted_at_utc(self) -> Optional[datetime]:
        """ Deletion date with UTC timezoneinfo"""
        if self.deleted_at:
            return self.deleted_at.replace(tzinfo=timezone.utc)
        return None

    def __repr__(self):
        return (f'Bot(id={self.id}, cg_bot_id={self.bot_id}, user_id={self.user_id})')

    def to_json(self, minified: bool = False) -> Dict[str, Any]:
        resp = {
            'bot_id': self.bot_id,
            'user_id': self.user_id,
            'state': self.state,
            'is_active': self.is_active,
            'is_strategy': self.is_strategy,
        }
        if not minified:
            resp.update({
                'strategy': self.strategy,
                'exchange': self.exchange,
                'created_at': self.created_at.strftime(DATETIME_PRINT_FORMAT),
                'updated_at': self.updated_at.strftime(DATETIME_PRINT_FORMAT)
                if self.updated_at else None,
                'deleted_at': self.deleted_at.strftime(DATETIME_PRINT_FORMAT)
                if self.deleted_at else None,
            })
        return resp

    # @staticmethod
    # def update_orders(orders: List['Order'], order: Dict[str, Any]):
    #     """
    #     Get all non-closed orders - useful when trying to batch-update orders
    #     """
    #     if not isinstance(order, dict):
    #         logger.warning(f"{order} is not a valid response object.")
    #         return

    #     filtered_orders = [o for o in orders if o.order_id == order.get('id')]
    #     if filtered_orders:
    #         oobj = filtered_orders[0]
    #         oobj.update_from_ccxt_object(order)
    #         Order.query.session.commit()
    #     else:
    #         logger.warning(f"Did not find order for {order}.")

    @staticmethod
    def get_active_bots() -> List['Bot']:
        """
        Retrieve active bots from the database
        :return: List of active bots
        """
        return Bot.query.filter(Bot.is_active.is_(True)).all()

    @staticmethod
    def get_strategy_bots() -> List['Bot']:
        """
        Retrieve active bots from the database
        :return: List of active bots
        """
        return Bot.query.filter(Bot.is_strategy.is_(True)).all()

    @staticmethod
    def bot_by_id(bot_id: str) -> Optional['Bot']:
        """
        Retrieve bot based on bot_id
        :return: Bot or None
        """
        return Bot.query.filter(Bot.bot_id == bot_id).first()

    @staticmethod
    def commit():
        Bot.query.session.commit()
