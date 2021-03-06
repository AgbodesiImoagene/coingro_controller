from typing import Any, Dict, Iterator, Optional

from fastapi import Depends, HTTPException, Request, status

from coingro.enums import RunMode
from coingro.rpc.rpc import RPCException

from coingro_controller.enums import Role
from coingro_controller.persistence import Bot, User
from coingro_controller.rpc.rpc import RPC
from coingro_controller.rpc.api_server.webserver import ApiServer
from coingro_controller.rpc.client import CoingroClient

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
        raise RPCException('Controller is not in the correct state')


def get_client() -> CoingroClient:
    return ApiServer._client


def get_config() -> Dict[str, Any]:
    return ApiServer._config


def get_api_config() -> Dict[str, Any]:
    return ApiServer._config['api_server']


def is_webserver_mode(config=Depends(get_config)):
    if config['runmode'] != RunMode.WEBSERVER:
        raise RPCException('Bot is not in the correct state')
    return None


def get_bot(bot_id: str, user: User = Depends(get_user)) -> Bot:
    bot = Bot.bot_by_id(bot_id)
    if (not bot) or (bot.deleted_at):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bot not found."
        )

    if (user.role == Role.USER) and (bot.user_id != user.id):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized."
        )

    return bot

def get_user(req: Request) -> User:
    user_id = req.headers.get("Authorization", '')
    user = User.user_by_id(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found."
        )
    return user
