import logging
from typing import Any, Dict, Iterator, Optional

from fastapi import Depends, Header, HTTPException, status

from coingro.enums import RunMode
from coingro.rpc.rpc import RPCException
from coingro_controller.enums import Role
from coingro_controller.persistence import Bot, User
from coingro_controller.rpc.api_server.webserver import ApiServer
from coingro_controller.rpc.client import CoingroClient
from coingro_controller.rpc.rpc import RPC

logger = logging.getLogger(__name__)


def get_rpc_optional() -> Optional[RPC]:
    if ApiServer._has_rpc:
        return ApiServer._rpc
    return None


def get_rpc() -> Optional[Iterator[RPC]]:
    _rpc = get_rpc_optional()
    if _rpc:
        User.query.session.rollback()
        yield _rpc
        User.query.session.rollback()
    else:
        raise RPCException("Controller is not in the correct state")


def get_client(rpc=Depends(get_rpc)) -> CoingroClient:
    return rpc._client


def get_config() -> Dict[str, Any]:
    return ApiServer._config


def get_bot_config(rpc=Depends(get_rpc)) -> Dict[str, Any]:
    return rpc._bot_config


def get_api_config() -> Dict[str, Any]:
    return ApiServer._config["api_server"]


def is_webserver_mode(config=Depends(get_config)):
    if config["runmode"] != RunMode.WEBSERVER:
        raise RPCException("Bot is not in the correct state")
    return None


def get_user(userid: int = Header(None)) -> Iterator[User]:
    User.query.session.rollback()
    user = User.user_by_id(userid)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")

    yield user
    User.query.session.rollback()


def get_bot(botid: str, user: User = Depends(get_user)) -> Iterator[Bot]:
    User.query.session.rollback()
    bot = Bot.bot_by_id(botid)
    if (not bot) or (bot.deleted_at):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bot not found.")

    if (user.role == Role.user) and (bot.user_id != user.id):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized.")

    yield bot
    User.query.session.rollback()


def get_active_bot(bot: Bot = Depends(get_bot)) -> Iterator[Bot]:
    User.query.session.rollback()
    if not bot.is_active:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bot is not active.")

    yield bot
    User.query.session.rollback()
