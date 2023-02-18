# pragma pylint: disable=missing-docstring, C0103
import argparse
from pathlib import Path
from unittest.mock import MagicMock

import pytest

import coingro
from coingro_controller.commands import ControllerArguments


# Parse common command-line-arguments. Used for all tools
def test_parse_args_none() -> None:
    arguments = ControllerArguments(["start"])
    assert isinstance(arguments, ControllerArguments)
    x = arguments.get_parsed_arg()
    assert isinstance(x, dict)
    assert isinstance(arguments.parser, argparse.ArgumentParser)


def test_parse_args_defaults(mocker) -> None:
    mocker.patch.object(Path, "is_file", MagicMock(side_effect=[False, True]))
    args = ControllerArguments(["start"]).get_parsed_arg()
    assert args["config"] == ["config.json"]
    assert args["verbosity"] == 0


def test_parse_args_defaults_docker(mocker) -> None:
    mocker.patch.object(Path, "is_file", MagicMock(side_effect=[True]))
    old_env = coingro.__env__
    coingro.__env__ = "docker"
    args = ControllerArguments(["start"]).get_parsed_arg()
    assert args["config"] == [str(Path("config/config.json"))]
    assert args["verbosity"] == 0
    coingro.__env__ = old_env


def test_parse_args_config() -> None:
    args = ControllerArguments(["start", "-c", "/dev/null"]).get_parsed_arg()
    assert args["config"] == ["/dev/null"]

    args = ControllerArguments(["start", "--config", "/dev/null"]).get_parsed_arg()
    assert args["config"] == ["/dev/null"]

    args = ControllerArguments(
        ["start", "--config", "/dev/null", "--config", "/dev/zero"],
    ).get_parsed_arg()
    assert args["config"] == ["/dev/null", "/dev/zero"]


def test_parse_args_db_url() -> None:
    args = ControllerArguments(["start", "--db-url", "sqlite:///test.sqlite"]).get_parsed_arg()
    assert args["db_url"] == "sqlite:///test.sqlite"


def test_parse_args_verbose() -> None:
    args = ControllerArguments(["start", "-v"]).get_parsed_arg()
    assert args["verbosity"] == 1

    args = ControllerArguments(["start", "--verbose"]).get_parsed_arg()
    assert args["verbosity"] == 1


def test_parse_args_version() -> None:
    with pytest.raises(SystemExit, match=r"0"):
        ControllerArguments(["--version"]).get_parsed_arg()


def test_parse_args_invalid() -> None:
    with pytest.raises(SystemExit, match=r"2"):
        ControllerArguments(["-c"]).get_parsed_arg()


def test_parse_args_strategy_invalid() -> None:
    with pytest.raises(SystemExit, match=r"2"):
        ControllerArguments(["--strategy"]).get_parsed_arg()


def test_parse_args_strategy_path() -> None:
    args = ControllerArguments(["start", "--strategy-path", "/some/path"]).get_parsed_arg()
    assert args["strategy_path"] == "/some/path"


def test_parse_args_strategy_path_invalid() -> None:
    with pytest.raises(SystemExit, match=r"2"):
        ControllerArguments(["--strategy-path"]).get_parsed_arg()
