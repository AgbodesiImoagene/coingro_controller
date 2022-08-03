"""
This module contains the class to persist trades into SQLite
"""
import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from coingro.constants import DATETIME_PRINT_FORMAT
from sqlalchemy import BigInteger, Column, DateTime, Enum, String
from sqlalchemy.orm import relationship

from coingro_controller.enums import Role
from coingro_controller.persistence.base import _DECL_BASE


logger = logging.getLogger(__name__)


class User(_DECL_BASE):  # Add collate to string columns
    """
    User database model
    Keeps a record of all users
    """
    __tablename__ = 'users'

    id = Column(BigInteger, primary_key=True)

    bots = relationship("Bot", order_by="Bot.id", cascade="all, delete-orphan",
                        lazy="joined", back_populates="user")

    fullname = Column(String(255), nullable=False)
    email = Column(String(255), nullable=False, unique=True)
    username = Column(String(255), nullable=False, unique=True)
    role = Column(Enum(Role), nullable=False, default=Role.user)

    authCode = Column(String(255), nullable=True)
    email_verified_at = Column(DateTime, nullable=True)
    password = Column(String(255), nullable=False)
    remember_token = Column(String(100), nullable=True)

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
        return (f'User(id={self.id}, username={self.username})')

    def to_json(self, minified: bool = False) -> Dict[str, Any]:
        resp = {
            'username': self.username,
            'fullname': self.fullname,
            'email': self.email,
        }
        if not minified:
            resp.update({
                'role': self.role,
                'hashed_password': self.password,
                'auth_code': self.authCode,
                'created_at': self.created_at.strftime(DATETIME_PRINT_FORMAT),
                'updated_at': self.updated_at.strftime(DATETIME_PRINT_FORMAT)
                if self.updated_at else None,
                'deleted_at': self.deleted_at.strftime(DATETIME_PRINT_FORMAT)
                if self.deleted_at else None,
            })
        return resp

    @staticmethod
    def user_by_id(user_id: int) -> Optional['User']:
        """
        Retrieve user based on user_id
        :return: User or None
        """
        return User.query.filter(User.id == user_id).first()

    @staticmethod
    def commit():
        User.query.session.commit()
