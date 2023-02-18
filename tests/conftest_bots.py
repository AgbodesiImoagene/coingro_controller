from datetime import datetime, timedelta

from coingro.enums import State
from coingro_controller.enums import Role
from coingro_controller.persistence import Bot, Strategy, User

default_config = {
    "max_open_trades": 3,
    "stake_currency": "USDT",
    "stake_amount": 20,
    "tradable_balance_ratio": 0.99,
    "fiat_display_currency": "USD",
    "amount_reserve_percent": 0.05,
    "amend_last_stake_amount": False,
    "last_stake_amount_min_ratio": 0.5,
    "dry_run": True,
    "dry_run_wallet": 1000,
    "cancel_open_orders_on_exit": True,
    "unfilledtimeout": {"entry": 10, "exit": 10, "exit_timeout_count": 3, "unit": "minutes"},
    "entry_pricing": {
        "price_side": "same",
        "use_order_book": True,
        "order_book_top": 1,
        "price_last_balance": 0.0,
        "check_depth_of_market": {"enabled": False, "bids_to_ask_delta": 1},
    },
    "exit_pricing": {
        "price_side": "same",
        "use_order_book": True,
        "order_book_top": 1,
        "price_last_balance": 0.0,
    },
    "exchange": {
        "name": "binance",
        "pair_whitelist": [".*/USDT"],
        "pair_blacklist": ["BNB/USDT"],
    },
    "edge": {
        "enabled": False,
        "process_throttle_secs": 3600,
        "calculate_since_number_of_days": 7,
        "allowed_risk": 0.01,
        "stoploss_range_min": -0.01,
        "stoploss_range_max": -0.1,
        "stoploss_range_step": -0.01,
        "minimum_winrate": 0.60,
        "minimum_expectancy": 0.20,
        "min_trade_number": 10,
        "max_trade_duration_minute": 1440,
        "remove_pumps": False,
    },
    "telegram": {
        "enabled": False,
        "token": "your_telegram_token",
        "chat_id": "your_telegram_chat_id",
        "notification_settings": {
            "status": "on",
            "warning": "on",
            "startup": "on",
            "entry": "on",
            "entry_fill": "on",
            "exit": {
                "roi": "off",
                "emergency_exit": "off",
                "force_exit": "off",
                "exit_signal": "off",
                "trailing_stop_loss": "off",
                "stop_loss": "off",
                "stoploss_on_exchange": "off",
                "custom_exit": "off",
            },
            "exit_fill": "on",
            "entry_cancel": "on",
            "exit_cancel": "on",
            "protection_trigger": "off",
            "protection_trigger_global": "on",
        },
        "reload": True,
        "balance_dust_level": 0.01,
    },
    "api_server": {
        "enabled": True,
        "listen_ip_address": "0.0.0.0",
        "listen_port": 8080,
        "verbosity": "error",
        "enable_openapi": True,
        "jwt_secret_key": "somethingrandom",
        "CORS_origins": [],
        "username": "coingro_bot",
        "password": "SuperSecurePassword",
    },
    "bot_name": "coingro_bot",
    "db_config": {"drivername": "sqlite", "database": "tradesv3.sqlite"},
    "initial_state": "stopped",
    "force_entry_enable": True,
    "internals": {"process_throttle_secs": 5, "heartbeat_interval": 60},
    "disable_dataframe_checks": False,
    "strategy": "Strategy01",
    "recursive_strategy_search": True,
    "add_config_files": [],
    "dataformat_ohlcv": "json",
    "dataformat_trades": "jsongz",
}


def mock_user_1():
    return User(
        id=1,
        fullname="Mock User 1",
        email="mock.user1@coingro.com",
        username="mock_user1",
        role=Role.user,
        password="abcdefgh",
    )


def mock_user_2():
    return User(
        id=2,
        fullname="Mock User 2",
        email="mock.user2@coingro.com",
        username="mock_user2",
        role=Role.user,
        password="12345678",
    )


def mock_bot_1(is_active: bool):
    return Bot(
        id=1,
        bot_name="bot_1",
        bot_id="coingro01",
        user_id=1,
        image="coingro",
        version="1.0.0",
        api_url="coingro01/api/v1",
        strategy="Strategy01",
        exchange="binance",
        stake_currency="USDT",
        state=State.RUNNING,
        is_active=is_active,
        is_strategy=False,
        configuration=default_config.update({"bot_name": "bot_1"}),
    )


def mock_bot_2(is_active: bool):
    return Bot(
        id=2,
        bot_name="bot_2",
        bot_id="coingro02",
        user_id=1,
        image="coingro",
        version="1.0.0",
        api_url="coingro02/api/v1",
        strategy="Strategy01",
        exchange="binance",
        stake_currency="USDT",
        state=State.RUNNING,
        is_active=is_active,
        is_strategy=False,
        configuration=default_config.update({"bot_name": "bot_2"}),
    )


def mock_bot_3(is_active: bool):
    return Bot(
        id=3,
        bot_name="bot_3",
        bot_id="coingro03",
        user_id=1,
        image="coingro",
        version="1.0.0",
        api_url="coingro03/api/v1",
        strategy="Strategy02",
        exchange="binance",
        stake_currency="USDT",
        state=State.STOPPED,
        is_active=is_active,
        is_strategy=False,
        configuration=default_config.update({"bot_name": "bot_3"}),
    )


def mock_bot_4(is_active: bool):
    return Bot(
        id=4,
        bot_name="bot_4",
        bot_id="coingro04",
        user_id=2,
        image="coingro",
        version="0.0.1",
        api_url="coingro04/api/v1",
        strategy="Strategy01",
        exchange="binance",
        stake_currency="USDT",
        state=State.RUNNING,
        is_active=is_active,
        is_strategy=False,
        configuration=default_config.update({"bot_name": "bot_4"}),
    )


def mock_bot_5(is_active: bool):
    return Bot(
        id=5,
        bot_name="bot_5",
        bot_id="coingro05",
        user_id=2,
        image="coingro",
        version="1.0.0",
        api_url="coingro05/api/v1",
        strategy="Strategy02",
        exchange="binance",
        stake_currency="USDT",
        state=State.STOPPED,
        is_active=is_active,
        is_strategy=False,
        configuration=default_config.update({"bot_name": "bot_5"}),
        deleted_at=datetime.utcnow(),
    )


def mock_bot_6(is_active: bool):
    return Bot(
        id=6,
        bot_name="Strategy01",
        bot_id="Strategy01",
        image="coingro",
        version="1.0.0",
        api_url="Strategy01/api/v1",
        strategy="Strategy01",
        exchange="binance",
        stake_currency="USDT",
        state=State.RUNNING,
        is_active=is_active,
        is_strategy=True,
        configuration=default_config.update({"bot_name": "bot_6"}),
    )


def mock_bot_7(is_active: bool):
    return Bot(
        id=7,
        bot_name="Strategy02",
        bot_id="Strategy02",
        image="coingro",
        version="1.0.0",
        api_url="Strategy02/api/v1",
        strategy="Strategy02",
        exchange="binance",
        stake_currency="USDT",
        state=State.RUNNING,
        is_active=is_active,
        is_strategy=True,
        configuration=default_config.update({"bot_name": "bot_7"}),
    )


def mock_bot_8(is_active: bool):
    return Bot(
        id=8,
        bot_name="Strategy03",
        bot_id="Strategy03",
        image="coingro",
        version="1.0.0",
        api_url="Strategy03/api/v1",
        strategy="Strategy03",
        exchange="binance",
        stake_currency="USDT",
        state=State.RUNNING,
        is_active=is_active,
        is_strategy=True,
        configuration=default_config.update({"bot_name": "bot_8"}),
        deleted_at=datetime.utcnow(),
    )


def mock_strategy_1(outdated: bool):
    return Strategy(
        id=1,
        strategy_name="Strategy01",
        bot_id=6,
        category="Test",
        latest_refresh=datetime.utcnow() - timedelta(hours=2) if outdated else datetime.utcnow(),
    )


def mock_strategy_2(outdated: bool):
    return Strategy(
        id=2,
        strategy_name="Strategy02",
        bot_id=7,
        category="Test",
        latest_refresh=datetime.utcnow() - timedelta(hours=2) if outdated else datetime.utcnow(),
    )


def mock_strategy_3(outdated: bool):
    return Strategy(
        id=3,
        strategy_name="Strategy03",
        bot_id=8,
        category="Test",
        latest_refresh=datetime.utcnow() - timedelta(hours=2) if outdated else datetime.utcnow(),
    )
