# pragma pylint: disable=missing-docstring

from copy import deepcopy
from pathlib import Path
from unittest.mock import MagicMock, PropertyMock

import pytest

from coingro.enums import State
from coingro.exceptions import CoingroException, OperationalException
from coingro_controller.commands import ControllerArguments
from coingro_controller.controller import Controller
from coingro_controller.main import main
from coingro_controller.worker import Worker
from tests.conftest import log_has, log_has_re, patched_configuration_load_config_file


def test_parse_args_None(caplog) -> None:
    with pytest.raises(SystemExit):
        main([])
    assert log_has_re(r"Usage of Coingro controller requires a subcommand.*", caplog)


def test_parse_start_controller(mocker) -> None:
    """
    Test that main() can start backtesting and also ensure we can pass some specific arguments
    further argument parsing is done in test_arguments.py
    """
    mocker.patch.object(Path, "is_file", MagicMock(side_effect=[False, True]))
    controller_mock = mocker.patch("coingro_controller.commands.start_controller")
    controller_mock.__name__ = PropertyMock("start_controller")
    # it's sys.exit(0) at the end of backtesting
    with pytest.raises(SystemExit):
        main(["start"])
    assert controller_mock.call_count == 1
    call_args = controller_mock.call_args[0][0]
    assert call_args["config"] == ["config.json"]
    assert call_args["verbosity"] == 0
    assert call_args["command"] == "start"
    assert call_args["func"] is not None
    assert callable(call_args["func"])


def test_main_cluster_exception(mocker, default_conf, caplog) -> None:
    mocker.patch("coingro_controller.commands.controller_commands.os.environ", {})
    mocker.patch("coingro_controller.commands.controller_commands.__env__", "")

    args = ["start"]

    # Test Main + the KeyboardInterrupt exception
    with pytest.raises(SystemExit):
        main(args)
    assert log_has("Coingro controller must be run within a kubernetes cluster.", caplog)


def test_main_fatal_exception(mocker, default_conf, caplog) -> None:
    env = {"KUBERNETES_SERVICE_HOST": "localhost"}
    mocker.patch("coingro_controller.commands.controller_commands.os.environ", env)
    mocker.patch("coingro_controller.commands.controller_commands.__env__", "kubernetes")
    mocker.patch("coingro_controller.controller.Controller.cleanup", MagicMock())
    mocker.patch("coingro_controller.worker.Worker._worker", MagicMock(side_effect=Exception))
    patched_configuration_load_config_file(mocker, default_conf)
    mocker.patch("coingro_controller.controller.RPCManager", MagicMock())
    mocker.patch("coingro_controller.controller.init_db", MagicMock())
    mocker.patch("coingro_controller.controller.Client", MagicMock())

    args = ["start"]

    # Test Main + the KeyboardInterrupt exception
    with pytest.raises(SystemExit):
        main(args)
    assert log_has("Using config: config/config.json ...", caplog)
    assert log_has("Fatal exception!", caplog)

    caplog.clear()
    mocker.patch(
        "coingro_controller.main.ControllerArguments.get_parsed_arg",
        MagicMock(side_effect=Exception),
    )

    with pytest.raises(SystemExit):
        main(args)
    assert log_has("Fatal exception!", caplog)


def test_main_keyboard_interrupt(mocker, default_conf, caplog) -> None:
    env = {"KUBERNETES_SERVICE_HOST": "localhost"}
    mocker.patch("coingro_controller.commands.controller_commands.os.environ", env)
    mocker.patch("coingro_controller.commands.controller_commands.__env__", "kubernetes")
    mocker.patch("coingro_controller.controller.Controller.cleanup", MagicMock())
    mocker.patch(
        "coingro_controller.worker.Worker._worker", MagicMock(side_effect=KeyboardInterrupt)
    )
    patched_configuration_load_config_file(mocker, default_conf)
    mocker.patch("coingro_controller.controller.RPCManager", MagicMock())
    mocker.patch("coingro_controller.controller.init_db", MagicMock())
    mocker.patch("coingro_controller.controller.Client", MagicMock())

    args = ["start"]

    # Test Main + the KeyboardInterrupt exception
    with pytest.raises(SystemExit):
        main(args)
    assert log_has("Using config: config/config.json ...", caplog)
    assert log_has("SIGINT received, aborting ...", caplog)

    caplog.clear()
    mocker.patch(
        "coingro_controller.main.ControllerArguments.get_parsed_arg",
        MagicMock(side_effect=KeyboardInterrupt),
    )

    with pytest.raises(SystemExit):
        main(args)
    assert log_has("SIGINT received, aborting ...", caplog)


def test_main_operational_exception(mocker, default_conf, caplog) -> None:
    env = {"KUBERNETES_SERVICE_HOST": "localhost"}
    mocker.patch("coingro_controller.commands.controller_commands.os.environ", env)
    mocker.patch("coingro_controller.commands.controller_commands.__env__", "kubernetes")
    mocker.patch("coingro_controller.controller.Controller.cleanup", MagicMock())
    mocker.patch(
        "coingro_controller.worker.Worker._worker",
        MagicMock(side_effect=CoingroException("Oh snap!")),
    )
    patched_configuration_load_config_file(mocker, default_conf)
    mocker.patch("coingro_controller.controller.RPCManager", MagicMock())
    mocker.patch("coingro_controller.controller.init_db", MagicMock())
    mocker.patch("coingro_controller.controller.Client", MagicMock())

    args = ["start"]

    # Test Main + the KeyboardInterrupt exception
    with pytest.raises(SystemExit):
        main(args)
    assert log_has("Using config: config/config.json ...", caplog)
    assert log_has("Oh snap!", caplog)

    caplog.clear()
    mocker.patch(
        "coingro_controller.main.ControllerArguments.get_parsed_arg",
        MagicMock(side_effect=CoingroException("Oh snap!")),
    )

    with pytest.raises(SystemExit):
        main(args)
    assert log_has("Oh snap!", caplog)


def test_main_reload_config(mocker, default_conf, caplog) -> None:
    env = {"KUBERNETES_SERVICE_HOST": "localhost"}
    mocker.patch("coingro_controller.commands.controller_commands.os.environ", env)
    mocker.patch("coingro_controller.commands.controller_commands.__env__", "kubernetes")
    mocker.patch("coingro_controller.controller.Controller.cleanup", MagicMock())
    # Simulate Running, reload, running workflow
    worker_mock = MagicMock(
        side_effect=[
            State.RUNNING,
            State.RELOAD_CONFIG,
            State.RUNNING,
            OperationalException("Oh snap!"),
        ]
    )
    mocker.patch("coingro_controller.worker.Worker._worker", worker_mock)
    patched_configuration_load_config_file(mocker, default_conf)
    reconfigure_mock = mocker.patch("coingro_controller.worker.Worker._reconfigure", MagicMock())

    mocker.patch("coingro_controller.controller.RPCManager", MagicMock())
    mocker.patch("coingro_controller.controller.init_db", MagicMock())
    mocker.patch("coingro_controller.controller.Client", MagicMock())

    args = ControllerArguments(["start"]).get_parsed_arg()
    worker = Worker(args=args, config=default_conf)
    with pytest.raises(SystemExit):
        main(["start"])

    assert log_has("Using config: config/config.json ...", caplog)
    assert worker_mock.call_count == 4
    assert reconfigure_mock.call_count == 1
    assert isinstance(worker.controller, Controller)


def test_reconfigure(mocker, default_conf) -> None:
    env = {"KUBERNETES_SERVICE_HOST": "localhost"}
    mocker.patch("coingro_controller.commands.controller_commands.os.environ", env)
    mocker.patch("coingro_controller.commands.controller_commands.__env__", "kubernetes")
    mocker.patch("coingro_controller.controller.Controller.cleanup", MagicMock())
    mocker.patch(
        "coingro_controller.worker.Worker._worker",
        MagicMock(side_effect=OperationalException("Oh snap!")),
    )
    patched_configuration_load_config_file(mocker, default_conf)
    mocker.patch("coingro_controller.controller.RPCManager", MagicMock())
    mocker.patch("coingro_controller.controller.init_db", MagicMock())
    mocker.patch("coingro_controller.controller.Client", MagicMock())

    args = ControllerArguments(["start"]).get_parsed_arg()
    worker = Worker(args=args, config=default_conf)
    controller = worker.controller

    # Renew mock to return modified data
    conf = deepcopy(default_conf)
    conf["cguser_group_id"] += 1
    patched_configuration_load_config_file(mocker, conf)

    worker._config = conf
    # reconfigure should return a new instance
    worker._reconfigure()
    controller2 = worker.controller

    # Verify we have a new instance with the new config
    assert controller is not controller2
    assert controller.config["cguser_group_id"] + 1 == controller2.config["cguser_group_id"]
