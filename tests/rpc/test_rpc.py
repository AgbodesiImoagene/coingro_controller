# pragma pylint: disable=missing-docstring, C0103
# pragma pylint: disable=invalid-sequence-index, invalid-name, too-many-arguments

from unittest.mock import MagicMock

import pytest

from coingro_controller.rpc import RPC
from tests.conftest import create_mock_bots, get_patched_controller


# Unit tests
def test_rpc_health(mocker, default_conf) -> None:
    controller = get_patched_controller(mocker, default_conf)
    rpc = RPC(controller)
    result = rpc._health()
    assert result["last_process"] == "1970-01-01 00:00:00+00:00"
    assert result["last_process_ts"] == 0


def test_rpc_exchange_info(mocker, default_conf) -> None:
    controller = get_patched_controller(mocker, default_conf)
    rpc = RPC(controller)
    result = rpc._rpc_exchange_info()
    assert isinstance(result["binance"], dict)


@pytest.mark.usefixtures("init_persistence")
def test_rpc_create_bot(mocker, default_conf) -> None:
    create_mock_bots()
    controller = get_patched_controller(mocker, default_conf)
    rpc = RPC(controller)

    mocker.patch(
        "coingro_controller.controller.Client.get_coingro_instance", MagicMock(return_value=None)
    )
    result = rpc._rpc_create_bot(1)
    assert isinstance(result["bot_id"], str)
    assert isinstance(result["bot_name"], str)
    assert result["status"] == "Successfully created coingro bot."


@pytest.mark.usefixtures("init_persistence")
def test_rpc_activate_bot(mocker, default_conf) -> None:
    create_mock_bots()
    controller = get_patched_controller(mocker, default_conf)
    rpc = RPC(controller)

    mocker.patch(
        "coingro_controller.controller.Client.get_coingro_instance", MagicMock(return_value=None)
    )
    result = rpc._rpc_activate_bot("coingro01")
    assert result["status"] == "Successfully activated coingro bot."


@pytest.mark.usefixtures("init_persistence")
def test_rpc_deactivate_bot(mocker, default_conf) -> None:
    create_mock_bots()
    controller = get_patched_controller(mocker, default_conf)
    rpc = RPC(controller)

    mocker.patch(
        "coingro_controller.controller.Client.get_coingro_instance", MagicMock(return_value=None)
    )
    result = rpc._rpc_deactivate_bot("coingro01")
    assert result["status"] == "Successfully deactivated coingro bot."


@pytest.mark.usefixtures("init_persistence")
def test_rpc_delete_bot(mocker, default_conf) -> None:
    create_mock_bots()
    controller = get_patched_controller(mocker, default_conf)
    rpc = RPC(controller)

    mocker.patch(
        "coingro_controller.controller.Client.get_coingro_instance", MagicMock(return_value=None)
    )
    result = rpc._rpc_delete_bot("coingro01")
    assert result["status"] == "Successfully deleted coingro bot."
