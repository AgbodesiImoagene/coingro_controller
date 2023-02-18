# pragma pylint: disable=missing-docstring, C0103
# pragma pylint: disable=protected-access, too-many-lines, invalid-name, too-many-arguments

from datetime import datetime
from unittest.mock import MagicMock

import pytest

from coingro.enums import State
from coingro_controller.controller import Controller
from coingro_controller.persistence import Bot
from tests.conftest import create_mock_bots, get_patched_controller, log_has, log_has_re
from tests.conftest_k8s import mock_pod


def patch_RPCManager(mocker) -> MagicMock:
    """
    This function mock RPC manager to avoid repeating this code in almost every tests
    :param mocker: mocker to patch RPCManager class
    :return: RPCManager.send_msg MagicMock to track if this method is called
    """
    rpc_mock = mocker.patch("coingro_controller.controller.RPCManager.send_msg", MagicMock())
    return rpc_mock


# Unit tests


def test_controller_state(mocker, default_conf) -> None:
    controller = get_patched_controller(mocker, default_conf)
    assert controller.state is State.RUNNING

    default_conf.pop("initial_state")
    controller = Controller(default_conf)
    assert controller.state is State.STOPPED


def test_controller_cleanup(mocker, default_conf, caplog) -> None:
    mock_cleanup = mocker.patch("coingro_controller.controller.cleanup_db")
    controller = get_patched_controller(mocker, default_conf)
    controller.cleanup()
    assert log_has("Cleaning up modules ...", caplog)
    assert mock_cleanup.call_count == 1


@pytest.mark.usefixtures("init_persistence")
def test_check_bots_1(mocker, default_conf) -> None:
    controller = get_patched_controller(mocker, default_conf)
    create_mock_bots()

    create_mock = mocker.patch("coingro_controller.controller.Controller.create_bot", MagicMock())
    mocker.patch(
        "coingro_controller.controller.Client.get_coingro_instance", MagicMock(side_effect=mock_pod)
    )
    controller.check_bots()
    assert create_mock.call_count == 1

    create_mock.reset_mock()
    mocker.patch(
        "coingro_controller.controller.Client.get_coingro_instance",
        MagicMock(
            side_effect=[
                mock_pod("default", "Failed"),
                mock_pod("default", "Failed"),
                mock_pod("default", "Running"),
                mock_pod("default", "Pending"),
                mock_pod("default", "Running"),
            ]
        ),
    )
    controller.check_bots()
    assert create_mock.call_count == 3


@pytest.mark.usefixtures("init_persistence")
def test_check_bots_2(mocker, default_conf) -> None:
    controller = get_patched_controller(mocker, default_conf)
    create_mock_bots(is_active=True)
    create_mock = mocker.patch("coingro_controller.controller.Controller.create_bot", MagicMock())
    mocker.patch(
        "coingro_controller.controller.Client.get_coingro_instance",
        MagicMock(
            side_effect=[
                mock_pod("default", "Failed"),
                mock_pod("default", "Failed"),
                mock_pod("default", "Running"),
                mock_pod("default", "Pending"),
                mock_pod("default", "Running"),
                mock_pod("default", "Failed"),
                mock_pod("default", "Pending"),
                mock_pod("default", "Running"),
            ]
        ),
    )
    controller.check_bots()
    assert create_mock.call_count == 4


@pytest.mark.usefixtures("init_persistence")
def test_refresh_strategies_1(mocker, default_conf, strategy_data) -> None:
    controller = get_patched_controller(mocker, default_conf)
    create_mock_bots()

    profit_mock = mocker.patch(
        "coingro_controller.controller.CoingroClient.profit",
        MagicMock(return_value=strategy_data["profit"]),
    )
    summary_mock = mocker.patch(
        "coingro_controller.controller.CoingroClient.trade_summary",
        MagicMock(return_value=strategy_data["trade_summary"]),
    )
    controller.refresh_strategies()
    assert profit_mock.call_count == 1
    assert summary_mock.call_count == 1


@pytest.mark.usefixtures("init_persistence")
def test_refresh_strategies_2(mocker, default_conf, strategy_data) -> None:
    controller = get_patched_controller(mocker, default_conf)
    create_mock_bots(is_active=True, outdated=True)

    profit_mock = mocker.patch(
        "coingro_controller.controller.CoingroClient.profit",
        MagicMock(return_value=strategy_data["profit"]),
    )
    summary_mock = mocker.patch(
        "coingro_controller.controller.CoingroClient.trade_summary",
        MagicMock(return_value=strategy_data["trade_summary"]),
    )
    controller.refresh_strategies()
    assert profit_mock.call_count == 3
    assert summary_mock.call_count == 3


@pytest.mark.usefixtures("init_persistence")
def test_refresh_strategies_3(mocker, default_conf, strategy_data, caplog) -> None:
    controller = get_patched_controller(mocker, default_conf)
    create_mock_bots(is_active=True, outdated=True)
    strategy_data.update({"trade_summary": {}})
    message = r"Could not update trade statistics for strategy .* due to .*\."

    mocker.patch(
        "coingro_controller.controller.CoingroClient.profit",
        MagicMock(return_value=strategy_data["profit"]),
    )
    mocker.patch(
        "coingro_controller.controller.CoingroClient.trade_summary",
        MagicMock(return_value=strategy_data["trade_summary"]),
    )
    controller.refresh_strategies()
    assert log_has_re(message, caplog)


@pytest.mark.usefixtures("init_persistence")
def test_check_strategies(mocker, default_conf, strategy_objects) -> None:
    controller = get_patched_controller(mocker, default_conf)
    create_mock_bots(is_active=True)

    mocker.patch(
        "coingro_controller.controller.Controller.get_strategy_objects",
        MagicMock(return_value=strategy_objects),
    )
    mocker.patch(
        "coingro_controller.controller.Client.get_coingro_instance", MagicMock(return_value=None)
    )
    create_mock = mocker.patch(
        "coingro_controller.controller.Client.create_coingro_instance", MagicMock()
    )
    deactivate_mock = mocker.patch(
        "coingro_controller.controller.Controller.deactivate_bot", MagicMock()
    )
    controller.check_strategies()
    assert create_mock.call_count == 2
    assert deactivate_mock.call_count == 1


@pytest.mark.usefixtures("init_persistence")
def test_create_bot(mocker, default_conf) -> None:
    controller = get_patched_controller(mocker, default_conf)
    create_mock_bots(is_active=False)

    mocker.patch(
        "coingro_controller.controller.Client.get_coingro_instance", MagicMock(return_value=None)
    )
    create_mock = mocker.patch(
        "coingro_controller.controller.Client.create_coingro_instance", MagicMock()
    )
    replace_mock = mocker.patch(
        "coingro_controller.controller.Client.replace_coingro_instance", MagicMock()
    )
    controller.create_bot(bot_id="coingro03", bot_name="bot_3")
    assert create_mock.call_count == 1
    assert Bot.bot_by_id("coingro03").is_active

    mocker.patch("coingro_controller.controller.Client.get_coingro_instance", MagicMock())
    bot_id, bot_name = controller.create_bot()
    assert replace_mock.call_count == 1
    assert Bot.bot_by_id(bot_id).bot_name == bot_name

    now = datetime.utcnow()
    controller.create_bot(bot_id="coingro04", bot_name="bot_4", update=True)
    assert Bot.bot_by_id("coingro04").updated_at > now


@pytest.mark.usefixtures("init_persistence")
def test_deactivate_bot(mocker, default_conf) -> None:
    controller = get_patched_controller(mocker, default_conf)
    create_mock_bots(is_active=True)

    delete_mock = mocker.patch(
        "coingro_controller.controller.Client.delete_coingro_instance", MagicMock()
    )
    controller.deactivate_bot(bot_id="coingro03")
    assert delete_mock.call_count == 1
    assert not Bot.bot_by_id("coingro03").is_active

    now = datetime.utcnow()
    controller.deactivate_bot(bot_id="coingro04", delete=True)
    assert delete_mock.call_count == 2
    assert not Bot.bot_by_id("coingro04").is_active
    assert Bot.bot_by_id("coingro04").deleted_at > now
