"""
This module contains the class to persist trades into SQLite
"""
import logging
import random
import time

from sqlalchemy import create_engine, event, inspect, select
from sqlalchemy.exc import NoSuchModuleError
from sqlalchemy.orm import scoped_session, sessionmaker
from sqlalchemy.pool import StaticPool

from coingro.exceptions import OperationalException
from coingro.persistence.migrations import check_migrate
from coingro.persistence.models import create_db, ping_connection

from coingro_controller.persistence.base import _DECL_BASE
from coingro_controller.persistence.bot import Bot
from coingro_controller.persistence.user import User


logger = logging.getLogger(__name__)


_SQL_DOCS_URL = 'http://docs.sqlalchemy.org/en/latest/core/engines.html#database-urls'


def init_db(db_url: str) -> None:
    """
    Initializes this module with the given config,
    registers all known command handlers
    and starts polling for message updates
    :param db_url: Database to use
    :return: None
    """
    kwargs = {}

    if db_url == 'sqlite:///':
        raise OperationalException(
            f'Bad db-url {db_url}. For in-memory database, please use `sqlite://`.')
    if db_url == 'sqlite://':
        kwargs.update({
            'poolclass': StaticPool,
        })
    # Take care of thread ownership
    if db_url.startswith('sqlite://'):
        kwargs.update({
            'connect_args': {'check_same_thread': False},
        })

    try:
        engine = create_engine(db_url, future=True, **kwargs)
    except NoSuchModuleError:
        raise OperationalException(f"Given value for db_url: '{db_url}' "
                                   f"is no valid database URL! (See {_SQL_DOCS_URL})")

    event.listen(engine, "engine_connect", ping_connection)

    create_db(db_url)

    # https://docs.sqlalchemy.org/en/13/orm/contextual.html#thread-local-scope
    # Scoped sessions proxy requests to the appropriate thread-local session.
    # We should use the scoped_session object - not a seperately initialized version
    User._session = scoped_session(sessionmaker(bind=engine, autoflush=True))
    User.query = User._session.query_property()
    Bot.query = User._session.query_property()
    # Strategy.query = User._session.query_property()

    previous_tables = inspect(engine).get_table_names()
    _DECL_BASE.metadata.create_all(engine)
    # check_migrate(engine, decl_base=_DECL_BASE, previous_tables=previous_tables)


def cleanup_db() -> None:
    """
    Flushes all pending operations to disk.
    :return: None
    """
    User.commit()
