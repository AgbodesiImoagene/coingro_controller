# pragma pylint: disable=missing-docstring, protected-access, invalid-name
import json
import logging
import sys
import warnings
from copy import deepcopy
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from jsonschema import ValidationError

from coingro.configuration.load_config import load_config_file
from coingro.exceptions import OperationalException
from coingro.loggers import CGBufferingHandler, setup_logging_pre
from coingro_controller.commands import ControllerArguments
from coingro_controller.configuration import Configuration
from coingro_controller.configuration.config_validation import validate_config_schema
from coingro_controller.constants import DEFAULT_DB_URL
from coingro_controller.loggers import _set_loggers, setup_logging
from tests.conftest import log_has, patched_configuration_load_config_file


def test_load_config_missing_attributes(default_conf) -> None:
    conf = deepcopy(default_conf)
    conf.pop("cg_api_server_port")

    with pytest.raises(ValidationError, match=r".*'cg_api_server_port' is a required property.*"):
        validate_config_schema(conf)

    conf = deepcopy(default_conf)
    conf.pop("cg_image")

    with pytest.raises(ValidationError, match=r".*'cg_image' is a required property.*"):
        validate_config_schema(conf)

    conf = deepcopy(default_conf)
    conf.pop("cg_version")

    with pytest.raises(ValidationError, match=r".*'cg_version' is a required property.*"):
        validate_config_schema(conf)

    conf = deepcopy(default_conf)
    conf.pop("api_server")

    with pytest.raises(ValidationError, match=r".*'api_server' is a required property.*"):
        validate_config_schema(conf)


def test_load_config_file(default_conf, mocker, caplog) -> None:
    del default_conf["user_data_dir"]
    file_mock = mocker.patch(
        "coingro.configuration.load_config.open",
        mocker.mock_open(read_data=json.dumps(default_conf)),
    )

    validated_conf = load_config_file("somefile")
    assert file_mock.call_count == 1
    assert validated_conf.items() >= default_conf.items()


def test_load_config_file_error(default_conf, mocker, caplog) -> None:
    del default_conf["user_data_dir"]
    filedata = json.dumps(default_conf).replace(
        '"cg_api_server_port": 8080,', '"cg_api_server_port": .8080,'
    )
    mocker.patch("coingro.configuration.load_config.open", mocker.mock_open(read_data=filedata))
    mocker.patch.object(Path, "read_text", MagicMock(return_value=filedata))

    with pytest.raises(OperationalException, match=r".*Please verify the following segment.*"):
        load_config_file("somefile")


def test_args_to_config(caplog):

    arg_list = ["start", "--strategy-path", "TestTest"]
    args = ControllerArguments(arg_list).get_parsed_arg()
    configuration = Configuration(args)
    config = {}
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        # No warnings ...
        configuration._args_to_config(config, argname="strategy_path", logstring="DeadBeef")
        assert len(w) == 0
        assert log_has("DeadBeef", caplog)
        assert config["strategy_path"] == "TestTest"

    configuration = Configuration(args)
    config = {}
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        # Deprecation warnings!
        configuration._args_to_config(
            config, argname="strategy_path", logstring="DeadBeef", deprecated_msg="Going away soon!"
        )
        assert len(w) == 1
        assert issubclass(w[-1].category, DeprecationWarning)
        assert "DEPRECATED: Going away soon!" in str(w[-1].message)
        assert log_has("DeadBeef", caplog)
        assert config["strategy_path"] == "TestTest"

    def log_fun(arg: str):
        return arg.upper()

    configuration = Configuration(args)
    config = {}
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        # Deprecation warnings!
        configuration._args_to_config(
            config,
            argname="strategy_path",
            logstring="DeadBeef: {}",
            logfun=log_fun,
            deprecated_msg="Going away soon!",
        )
        assert len(w) == 1
        assert issubclass(w[-1].category, DeprecationWarning)
        assert "DEPRECATED: Going away soon!" in str(w[-1].message)
        assert log_has("DeadBeef: TESTTEST", caplog)
        assert config["strategy_path"] == "TestTest"


def test_load_config_with_params(default_conf, mocker) -> None:
    patched_configuration_load_config_file(mocker, default_conf)

    arglist = [
        "start",
        "--strategy-path",
        "/some/path",
        "--db-url",
        "sqlite:///someurl",
    ]
    args = ControllerArguments(arglist).get_parsed_arg()
    configuration = Configuration(args)
    validated_conf = configuration.load_config()

    assert validated_conf.get("strategy_path") == "/some/path"
    assert validated_conf.get("db_url") == "sqlite:///someurl"

    # Test conf provided db_url prod
    conf = default_conf.copy()
    conf["db_url"] = "sqlite:///path/to/db.sqlite"
    patched_configuration_load_config_file(mocker, conf)

    arglist = ["start", "--strategy-path", "/some/path"]
    args = ControllerArguments(arglist).get_parsed_arg()

    configuration = Configuration(args)
    validated_conf = configuration.load_config()
    assert validated_conf.get("db_url") == "sqlite:///path/to/db.sqlite"

    # Test args provided db_url prod
    conf = default_conf.copy()
    del conf["db_url"]
    patched_configuration_load_config_file(mocker, conf)

    arglist = ["start", "--strategy-path", "/some/path"]
    args = ControllerArguments(arglist).get_parsed_arg()

    configuration = Configuration(args)
    validated_conf = configuration.load_config()
    assert validated_conf.get("db_url") == DEFAULT_DB_URL

    # Test static from_files method
    arglist = [
        "start",
    ]
    args = ControllerArguments(arglist).get_parsed_arg()

    configuration = Configuration(args)
    validated_conf = configuration.load_config()
    validated_conf2 = Configuration.from_files(args.get("config", []))
    assert validated_conf == validated_conf2


def test_show_info(default_conf, mocker, caplog) -> None:
    patched_configuration_load_config_file(mocker, default_conf)

    arglist = [
        "start",
        "--db-url",
        "sqlite:///tmp/testdb",
    ]
    args = ControllerArguments(arglist).get_parsed_arg()

    configuration = Configuration(args)
    configuration.get_config()

    assert log_has('Using DB: "sqlite:///tmp/testdb"', caplog)


def test_setup_configuration_without_arguments(mocker, default_conf, caplog) -> None:
    patched_configuration_load_config_file(mocker, default_conf)

    arglist = [
        "start",
        "--config",
        "config.json",
    ]

    args = ControllerArguments(arglist).get_parsed_arg()

    configuration = Configuration(args)
    config = configuration.get_config()
    assert "namespace" in config
    assert "cg_image" in config
    assert "cg_version" in config
    assert "cg_initial_state" in config
    assert "cg_env_vars" in config
    assert "cg_api_router_prefix" in config
    assert "cguser_group_id" in config
    assert "db_url" in config


def test_setup_configuration_with_arguments(mocker, default_conf, caplog) -> None:
    patched_configuration_load_config_file(mocker, default_conf)
    mocker.patch(
        "coingro_controller.configuration.configuration.create_userdata_dir",
        lambda x, *args, **kwargs: Path(x),
    )
    arglist = [
        "start",
        "--config",
        "config.json",
        "--strategy-path",
        "/some/path",
        "--userdir",
        "/tmp/coingro",
        "--db-url",
        "sqlite:///tmp/testdb",
        "--sd-notify",
    ]

    args = ControllerArguments(arglist).get_parsed_arg()

    configuration = Configuration(args)
    config = configuration.get_config()
    assert "namespace" in config
    assert "cg_image" in config
    assert "cg_version" in config
    assert "cg_initial_state" in config
    assert "cg_env_vars" in config
    assert "cg_api_router_prefix" in config
    assert "cguser_group_id" in config
    assert "strategy_path" in config
    assert "db_url" in config
    assert "sd_notify" in config["internals"]

    assert log_has("Using user-data directory: {} ...".format(Path("/tmp/coingro")), caplog)
    assert "user_data_dir" in config


def test_cli_verbose_with_params(default_conf, mocker, caplog) -> None:
    patched_configuration_load_config_file(mocker, default_conf)

    # Prevent setting loggers
    mocker.patch("coingro_controller.loggers._set_loggers", MagicMock)
    arglist = ["start", "-vvv"]
    args = ControllerArguments(arglist).get_parsed_arg()

    configuration = Configuration(args)
    validated_conf = configuration.load_config()

    assert validated_conf.get("verbosity") == 3
    assert log_has("Verbosity set to 3", caplog)


def test_set_loggers() -> None:
    # Reset Logging to Debug, otherwise this fails randomly as it's set globally
    logging.getLogger("requests").setLevel(logging.DEBUG)
    logging.getLogger("urllib3").setLevel(logging.DEBUG)
    logging.getLogger("telegram").setLevel(logging.DEBUG)

    previous_value1 = logging.getLogger("requests").level
    previous_value2 = logging.getLogger("telegram").level

    _set_loggers()

    value1 = logging.getLogger("requests").level
    assert previous_value1 is not value1
    assert value1 is logging.INFO

    value2 = logging.getLogger("telegram").level
    assert previous_value2 is not value2
    assert value2 is logging.INFO

    _set_loggers(verbosity=2)

    assert logging.getLogger("requests").level is logging.DEBUG
    assert logging.getLogger("telegram").level is logging.INFO
    assert logging.getLogger("werkzeug").level is logging.INFO

    _set_loggers(verbosity=3, api_verbosity="error")

    assert logging.getLogger("requests").level is logging.DEBUG
    assert logging.getLogger("telegram").level is logging.INFO
    assert logging.getLogger("werkzeug").level is logging.ERROR


@pytest.mark.skipif(sys.platform == "win32", reason="does not run on windows")
def test_set_loggers_syslog():
    logger = logging.getLogger()
    orig_handlers = logger.handlers
    logger.handlers = []

    config = {
        "verbosity": 2,
        "logfile": "syslog:/dev/log",
    }

    setup_logging_pre()
    setup_logging(config)
    assert len(logger.handlers) == 3
    assert [x for x in logger.handlers if type(x) == logging.handlers.SysLogHandler]
    assert [x for x in logger.handlers if type(x) == logging.StreamHandler]
    assert [x for x in logger.handlers if type(x) == CGBufferingHandler]
    # setting up logging again should NOT cause the loggers to be added a second time.
    setup_logging(config)
    assert len(logger.handlers) == 3
    # reset handlers to not break pytest
    logger.handlers = orig_handlers


@pytest.mark.skipif(sys.platform == "win32", reason="does not run on windows")
def test_set_loggers_Filehandler(tmpdir):
    logger = logging.getLogger()
    orig_handlers = logger.handlers
    logger.handlers = []
    logfile = Path(tmpdir) / "cg_logfile.log"
    config = {
        "verbosity": 2,
        "logfile": str(logfile),
    }

    setup_logging_pre()
    setup_logging(config)
    assert len(logger.handlers) == 3
    assert [x for x in logger.handlers if type(x) == logging.handlers.RotatingFileHandler]
    assert [x for x in logger.handlers if type(x) == logging.StreamHandler]
    assert [x for x in logger.handlers if type(x) == CGBufferingHandler]
    # setting up logging again should NOT cause the loggers to be added a second time.
    setup_logging(config)
    assert len(logger.handlers) == 3
    # reset handlers to not break pytest
    if logfile.exists:
        logfile.unlink()
    logger.handlers = orig_handlers


@pytest.mark.skipif(sys.platform == "win32", reason="does not run on windows")
def test_set_loggers_Filehandler_default():
    logger = logging.getLogger()
    orig_handlers = logger.handlers
    logger.handlers = []
    logfile = "default"
    config = {
        "verbosity": 2,
        "logfile": logfile,
        "user_data_dir": "user_data",
    }

    setup_logging_pre()
    setup_logging(config)
    assert len(logger.handlers) == 3
    assert [x for x in logger.handlers if type(x) == logging.handlers.RotatingFileHandler]
    assert [x for x in logger.handlers if type(x) == logging.StreamHandler]
    assert [x for x in logger.handlers if type(x) == CGBufferingHandler]
    # setting up logging again should NOT cause the loggers to be added a second time.
    setup_logging(config)
    assert len(logger.handlers) == 3
    # reset handlers to not break pytest
    logger.handlers = orig_handlers


@pytest.mark.skip(reason="systemd is not installed on every system, so we're not testing this.")
def test_set_loggers_journald(mocker):
    logger = logging.getLogger()
    orig_handlers = logger.handlers
    logger.handlers = []

    config = {
        "verbosity": 2,
        "logfile": "journald",
    }

    setup_logging(config)
    assert len(logger.handlers) == 2
    assert [x for x in logger.handlers if type(x).__name__ == "JournaldLogHandler"]
    assert [x for x in logger.handlers if type(x) == logging.StreamHandler]
    # reset handlers to not break pytest
    logger.handlers = orig_handlers


def test_set_loggers_journald_importerror(mocker, import_fails):
    logger = logging.getLogger()
    orig_handlers = logger.handlers
    logger.handlers = []

    config = {
        "verbosity": 2,
        "logfile": "journald",
    }
    with pytest.raises(OperationalException, match=r"You need the systemd python package.*"):
        setup_logging(config)
    logger.handlers = orig_handlers


def test_set_logfile(default_conf, mocker, tmpdir):
    patched_configuration_load_config_file(mocker, default_conf)
    f = Path(tmpdir / "test_file.log")
    assert not f.is_file()
    arglist = [
        "start",
        "--logfile",
        str(f),
    ]
    args = ControllerArguments(arglist).get_parsed_arg()
    configuration = Configuration(args)
    validated_conf = configuration.load_config()

    assert validated_conf["logfile"] == str(f)
    assert f.is_file()
    try:
        f.unlink()
    except Exception:
        pass


def test_validate_default_conf(default_conf) -> None:
    # Validate via our validator - we allow setting defaults!
    validate_config_schema(default_conf)


def test_db_url_from_config(default_conf, mocker):
    assert Configuration.db_url_from_config(default_conf) == "sqlite://"

    default_conf.pop("db_url")
    assert Configuration.db_url_from_config(default_conf) == DEFAULT_DB_URL

    default_conf["db_url"] = "sqlite:///testdb"
    assert Configuration.db_url_from_config(default_conf) == "sqlite:///testdb"

    default_conf.pop("db_url")
    db_args = {
        "drivername": "mysql",
        "username": "test-user",
        "password": "Password123",
        "host": "test-host",
        "port": 1234,
    }
    default_conf["db_config"] = db_args
    url = "mysql+pymysql://test-user:Password123@test-host:1234/coingro_k8s_controller"
    assert Configuration.db_url_from_config(default_conf) == url

    db_args = {
        "drivername": "postgresql",
        "username": "test-user",
        "password": "Password123",
        "host": "test-host",
        "port": 1234,
    }
    default_conf["db_config"] = db_args
    url = "postgresql+psycopg2://test-user:Password123@test-host:1234/coingro_k8s_controller"
    assert Configuration.db_url_from_config(default_conf) == url

    db_args = {"drivername": "sqlite", "database": "testdb2"}
    default_conf["db_config"] = db_args
    assert Configuration.db_url_from_config(default_conf) == "sqlite:///testdb2"


def test_user_data_dir(mocker, default_conf, caplog) -> None:
    default_conf.pop("user_data_dir")
    patched_configuration_load_config_file(mocker, default_conf)
    mocker.patch(
        "coingro_controller.configuration.configuration.Path.is_dir",
        MagicMock(side_effect=[True, False, True]),
    )
    mocker.patch(
        "coingro_controller.configuration.configuration.create_userdata_dir",
        lambda x, *args, **kwargs: Path(x),
    )

    arglist = [
        "start",
    ]

    args = ControllerArguments(arglist).get_parsed_arg()

    configuration = Configuration(args)
    config = configuration.get_config()
    assert config["user_data_dir"] == Path("/coingro/user_data")
    assert log_has("Using user-data directory: /coingro/user_data ...", caplog)

    configuration = Configuration(args)
    config = configuration.get_config()
    assert config["user_data_dir"] == Path("user_data")
    assert log_has("Using user-data directory: user_data ...", caplog)
