# pragma pylint: disable=missing-docstring, C0103
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from coingro.exceptions import OperationalException
from coingro_controller.constants import DEFAULT_DB_URL
from coingro_controller.persistence import User, init_db


def test_init_create_session(default_conf):
    # Check if init create a session
    init_db(default_conf["db_url"])
    assert hasattr(User, "_session")
    assert "scoped_session" in type(User._session).__name__


def test_init_custom_db_url(default_conf, tmpdir):
    # Update path to a value other than default, but still in-memory
    filename = f"{tmpdir}/coingro_controller_test.sqlite"
    assert not Path(filename).is_file()

    default_conf.update({"db_url": f"sqlite:///{filename}"})

    init_db(default_conf["db_url"])
    assert Path(filename).is_file()
    # r = User._session.execute(text("PRAGMA journal_mode"))
    # assert r.first() == ('wal',)


def test_init_invalid_db_url():
    # Update path to a value other than default, but still in-memory
    with pytest.raises(OperationalException, match=r".*no valid database URL*"):
        init_db("unknown:///some.url")

    with pytest.raises(OperationalException, match=r"Bad db-url.*For in-memory database, pl.*"):
        init_db("sqlite:///")


def test_init_db(default_conf, mocker):
    default_conf.update({"db_url": DEFAULT_DB_URL})

    create_engine_mock = mocker.patch(
        "coingro_controller.persistence.models.create_engine", MagicMock()
    )
    mocker.patch("coingro_controller.persistence.models.event.listen", MagicMock())

    init_db(default_conf["db_url"])
    assert create_engine_mock.call_count == 1
    assert create_engine_mock.mock_calls[0][1][0] == "sqlite:///controllerv1.sqlite"
