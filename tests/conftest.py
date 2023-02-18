# # pragma pylint: disable=missing-docstring
# import json
import logging
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional
from unittest.mock import MagicMock, Mock  # , PropertyMock

import pytest

from coingro.strategy import IStrategy
from coingro_controller.commands import ControllerArguments
from coingro_controller.controller import Controller
from coingro_controller.persistence import User, init_db
from coingro_controller.worker import Worker
from tests.conftest_bots import (
    mock_bot_1,
    mock_bot_2,
    mock_bot_3,
    mock_bot_4,
    mock_bot_5,
    mock_bot_6,
    mock_bot_7,
    mock_bot_8,
    mock_strategy_1,
    mock_strategy_2,
    mock_strategy_3,
    mock_user_1,
    mock_user_2,
)

logging.getLogger("").setLevel(logging.INFO)


# # Do not mask numpy errors as warnings that no one read, raise the exсeption
# np.seterr(all='raise')

# CURRENT_TEST_STRATEGY = 'StrategyTestV3'
# TRADE_SIDES = ('long', 'short')


def pytest_addoption(parser):
    parser.addoption(
        "--longrun",
        action="store_true",
        dest="longrun",
        default=False,
        help="Enable long-run tests (ccxt compat)",
    )


def pytest_configure(config):
    config.addinivalue_line(
        "markers", "longrun: mark test that is running slowly and should not be run regularily"
    )
    if not config.option.longrun:
        setattr(config.option, "markexpr", "not longrun")


def log_has(line, logs):
    """Check if line is found on some caplog's message."""
    return any(line == message for message in logs.messages)


def log_has_re(line, logs):
    """Check if line matches some caplog's message."""
    return any(re.match(line, message) for message in logs.messages)


def num_log_has(line, logs):
    """Check how many times line is found in caplog's messages."""
    return sum(line == message for message in logs.messages)


def num_log_has_re(line, logs):
    """Check how many times line matches caplog's messages."""
    return sum(bool(re.match(line, message)) for message in logs.messages)


def get_args(args):
    return ControllerArguments(args).get_parsed_arg()


# Source: https://stackoverflow.com/questions/29881236/how-to-mock-asyncio-coroutines
# TODO: This should be replaced with AsyncMock once support for python 3.7 is dropped.
def get_mock_coro(return_value=None, side_effect=None):
    async def mock_coro(*args, **kwargs):
        if side_effect:
            if isinstance(side_effect, list):
                effect = side_effect.pop(0)
            else:
                effect = side_effect
            if isinstance(effect, Exception):
                raise effect
            if callable(effect):
                return effect(*args, **kwargs)
            return effect
        else:
            return return_value

    return Mock(wraps=mock_coro)


def patched_configuration_load_config_file(mocker, config) -> None:
    mocker.patch(
        "coingro_controller.configuration.configuration.load_config_file",
        lambda *args, **kwargs: config,
    )


# Functions for recurrent object patching


def patch_controller(mocker, config) -> None:
    """
    This function patch _init_modules() to not call dependencies
    :param mocker: a Mocker object to apply patches
    :param config: Config to pass to the bot
    :return: None
    """
    mocker.patch("coingro_controller.controller.RPCManager", MagicMock())
    mocker.patch("coingro_controller.controller.RPCManager._init", MagicMock())
    mocker.patch("coingro_controller.controller.RPCManager.send_msg", MagicMock())
    mocker.patch("coingro_controller.k8s.client.k8s_config", MagicMock())
    mocker.patch("coingro_controller.k8s.client.client.CoreV1Api", MagicMock())


def get_patched_controller(mocker, config) -> Controller:
    """
    This function patches _init_modules() to not call dependencies
    :param mocker: a Mocker object to apply patches
    :param config: Config to pass to the bot
    :return: Controller
    """
    patch_controller(mocker, config)
    return Controller(config)


def get_patched_worker(mocker, config) -> Worker:
    """
    This function patches _init_modules() to not call dependencies
    :param mocker: a Mocker object to apply patches
    :param config: Config to pass to the bot
    :return: Worker
    """
    patch_controller(mocker, config)
    return Worker(args=None, config=config)


def create_mock_bots(is_active: Optional[bool] = None, outdated: Optional[bool] = None):
    is_active1 = is_active if is_active is not None else True
    is_active2 = is_active if is_active is not None else False

    outdated1 = outdated if outdated is not None else True
    outdated2 = outdated if outdated is not None else False

    user = mock_user_1()
    User.query.session.add(user)

    user = mock_user_2()
    User.query.session.add(user)

    bot = mock_bot_1(is_active1)
    User.query.session.add(bot)

    bot = mock_bot_2(is_active2)
    User.query.session.add(bot)

    bot = mock_bot_3(is_active1)
    User.query.session.add(bot)

    bot = mock_bot_4(is_active1)
    User.query.session.add(bot)

    bot = mock_bot_5(is_active2)
    User.query.session.add(bot)

    bot = mock_bot_6(is_active2)
    User.query.session.add(bot)

    bot = mock_bot_7(is_active1)
    User.query.session.add(bot)

    bot = mock_bot_8(is_active1)
    User.query.session.add(bot)

    strategy = mock_strategy_1(outdated1)
    User.query.session.add(strategy)

    strategy = mock_strategy_2(outdated2)
    User.query.session.add(strategy)

    strategy = mock_strategy_3(outdated1)
    User.query.session.add(strategy)

    User.commit()


@pytest.fixture(scope="function")
def init_persistence(default_conf):
    init_db(default_conf["db_url"])


@pytest.fixture(scope="function")
def default_conf():
    return get_default_conf()


def get_default_conf():
    """Returns validated configuration suitable for most tests"""
    configuration = {
        "namespace": "coingro",
        "cg_image": "coingro:1.0.0",
        "cg_env_vars": {},
        "cg_initial_state": "stopped",
        "cg_api_router_prefix": "api/v1",
        "cg_api_server_port": 8080,
        "cg_user_data_pvc_claim": "user-data-pvc",
        "cg_strategies_pvc_claim": "strategies-pvc",
        "cg_version": "1.0.0",
        "cguser_group_id": 1000,
        "api_server": {
            "enabled": False,
            "enable_openapi": False,
            "listen_ip_address": "0.0.0.0",
            "listen_port": 8080,
            "verbosity": "error",
        },
        "db_url": "sqlite://",
        "initial_state": "running",
        "user_data_dir": Path("user_data"),
    }
    return configuration


@pytest.fixture(scope="function")
def strategy_data():
    return {
        "profit": {
            "profit_closed_coin": 0.1,
            "profit_closed_percent_mean": 0.1,
            "profit_closed_ratio_mean": 0.1,
            "profit_closed_percent_sum": 0.1,
            "profit_closed_ratio_sum": 0.1,
            "profit_closed_percent": 0.1,
            "profit_closed_ratio": 0.1,
            "profit_closed_fiat": 0.1,
            "profit_all_coin": 0.1,
            "profit_all_percent_mean": 0.1,
            "profit_all_ratio_mean": 0.1,
            "profit_all_percent_sum": 0.1,
            "profit_all_ratio_sum": 0.1,
            "profit_all_percent": 0.1,
            "profit_all_ratio": 0.1,
            "profit_all_fiat": 0.1,
            "trade_count": 1,
            "closed_trade_count": 1,
            "first_trade_date": str(datetime.utcnow() - timedelta(days=1)),
            "first_trade_timestamp": 1,
            "latest_trade_date": str(datetime.utcnow() - timedelta(days=1)),
            "latest_trade_timestamp": 1,
            "avg_duration": "1 day 00:00:00",
            "best_pair": "ETH/BTC",
            "best_rate": 0.1,
            "best_pair_profit_ratio": 0.1,
            "winning_trades": 1,
            "losing_trades": 0,
            "profit_factor": 0.1,
            "max_drawdown": 0.1,
            "max_drawdown_abs": 0.1,
            "trading_volume": 0.1,
        },
        "trade_summary": {
            "daily": {
                "data": [
                    {
                        "date": str(datetime.utcnow() - timedelta(days=1)),
                        "abs_profit": 0.1,
                        "rel_profit": 0.1,
                        "starting_balance": 0.1,
                        "fiat_value": 0.1,
                        "trade_count": 1,
                    }
                ],
                "fiat_display_currency": "USD",
                "stake_currency": "BTC",
            },
            "weekly": {
                "data": [
                    {
                        "date": str(datetime.utcnow() - timedelta(days=1)),
                        "abs_profit": 0.1,
                        "rel_profit": 0.1,
                        "starting_balance": 0.1,
                        "fiat_value": 0.1,
                        "trade_count": 1,
                    }
                ],
                "fiat_display_currency": "USD",
                "stake_currency": "BTC",
            },
            "monthly": {
                "data": [
                    {
                        "date": str(datetime.utcnow() - timedelta(days=1)),
                        "abs_profit": 0.1,
                        "rel_profit": 0.1,
                        "starting_balance": 0.1,
                        "fiat_value": 0.1,
                        "trade_count": 1,
                    }
                ],
                "fiat_display_currency": "USD",
                "stake_currency": "BTC",
            },
        },
    }


def strategy_factory(name):
    class TestStrategy(IStrategy):
        __strategy_name__ = name

    return TestStrategy


@pytest.fixture(scope="function")
def strategy_objects():
    return [
        {"name": "Strategy01", "class": strategy_factory("Strategy01"), "Location": None},
        {"name": "Strategy03", "class": strategy_factory("Strategy03"), "Location": None},
        {"name": "Strategy04", "class": strategy_factory("Strategy04"), "Location": None},
        {"name": "Strategy05", "class": strategy_factory("Strategy05"), "Location": None},
    ]


@pytest.fixture
def testdatadir() -> Path:
    """Return the path where testdata files are stored"""
    return (Path(__file__).parent / "testdata").resolve()


@pytest.fixture(scope="function")
def import_fails() -> None:
    # Source of this test-method:
    # https://stackoverflow.com/questions/2481511/mocking-importerror-in-python
    import builtins

    realimport = builtins.__import__

    def mockedimport(name, *args, **kwargs):
        if name in ["filelock", "systemd.journal", "uvloop"]:
            raise ImportError(f"No module named '{name}'")
        return realimport(name, *args, **kwargs)

    builtins.__import__ = mockedimport

    # Run test - then cleanup
    yield

    # restore previous importfunction
    builtins.__import__ = realimport
