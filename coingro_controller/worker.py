"""
Main Coingro controller worker class.
"""
import logging
import time
import traceback
from os import getpid
from pathlib import Path
from typing import Any, Callable, Dict, Optional

import sdnotify

from coingro import __env__
from coingro.coingrobot import CoingroBot
from coingro.constants import (DEFAULT_CONFIG_SAVE, PROCESS_THROTTLE_SECS, RETRY_TIMEOUT,
                               USERPATH_CONFIG)
from coingro.enums import State
from coingro.exceptions import ExchangeError, OperationalException, TemporaryError

from coingro_controller import __version__
from coingro_controller.configuration import Configuration, validate_config_consistency
from coingro_controller.controller import Controller


logger = logging.getLogger(__name__)


class Worker:
    """
    Coingro controller worker class
    """

    def __init__(self, args: Dict[str, Any], config: Dict[str, Any] = None) -> None:
        """
        Init all variables and objects the bot needs to work
        """
        logger.info(f"Starting worker {__version__}")

        self._args = args
        self._config = config
        self._init(False)

        logger.info(self._config)

        self.last_throttle_start_time: float = 0
        self._heartbeat_msg: float = 0

        # Tell systemd that we completed initialization phase
        self._notify("READY=1")

    def _init(self, reconfig: bool) -> None:
        """
        Also called from the _reconfigure() method (with reconfig=True).
        """
        if reconfig or self._config is None:
            # Load configuration
            self._config = Configuration(self._args).get_config()

        validate_config_consistency(self._config)

        # # Init the instance of the bot
        # self.coingro = CoingroBot(self._config)

        self.controller = Controller(self._config)

        internals_config = self._config.get('internals', {})
        self._throttle_secs = internals_config.get('process_throttle_secs',
                                                   PROCESS_THROTTLE_SECS)
        self._heartbeat_interval = internals_config.get('heartbeat_interval', 60)

        self._sd_notify = sdnotify.SystemdNotifier() if \
            self._config.get('internals', {}).get('sd_notify', False) else None

    def _notify(self, message: str) -> None:
        """
        Removes the need to verify in all occurrences if sd_notify is enabled
        :param message: Message to send to systemd if it's enabled.
        """
        if self._sd_notify:
            logger.debug(f"sd_notify: {message}")
            self._sd_notify.notify(message)

    def run(self) -> None:
        state = None
        while True:
            state = self._worker(old_state=state)
            if state == State.RELOAD_CONFIG:
                self._reconfigure()

    def _worker(self, old_state: Optional[State]) -> State:
        """
        The main routine that runs each throttling iteration and handles the states.
        :param old_state: the previous service state from the previous call
        :return: current service state
        """
        # state = self.coingro.state

        # Log state transition
        if state != old_state:

            if old_state != State.RELOAD_CONFIG:
                # self.coingro.notify_status(f'{state.name.lower()}')

            logger.info(
                f"Changing state{f' from {old_state.name}' if old_state else ''} to: {state.name}")
            if state == State.RUNNING:
                # self.coingro.startup()

            if state == State.STOPPED:
                # self.coingro.check_for_open_trades()

            # Reset heartbeat timestamp to log the heartbeat message at
            # first throttling iteration when the state changes
            self._heartbeat_msg = 0

        if state == State.STOPPED:
            # Ping systemd watchdog before sleeping in the stopped state
            self._notify("WATCHDOG=1\nSTATUS=State: STOPPED.")

            self._throttle(func=self._process_stopped, throttle_secs=self._throttle_secs)

        elif state == State.RUNNING:
            # Ping systemd watchdog before throttling
            self._notify("WATCHDOG=1\nSTATUS=State: RUNNING.")

            self._throttle(func=self._process_running, throttle_secs=self._throttle_secs)

        if self._heartbeat_interval:
            now = time.time()
            if (now - self._heartbeat_msg) > self._heartbeat_interval:
                version = __version__
                # strategy_version = self.coingro.strategy.version()
                if (strategy_version is not None):
                    version += ', strategy_version: ' + strategy_version
                logger.info(f"Bot heartbeat. PID={getpid()}, "
                            f"version='{version}', state='{state.name}'")
                self._heartbeat_msg = now

        return state

    def _throttle(self, func: Callable[..., Any], throttle_secs: float, *args, **kwargs) -> Any:
        """
        Throttles the given callable that it
        takes at least `min_secs` to finish execution.
        :param func: Any callable
        :param throttle_secs: throttling interation execution time limit in seconds
        :return: Any (result of execution of func)
        """
        self.last_throttle_start_time = time.time()
        logger.debug("========================================")
        result = func(*args, **kwargs)
        time_passed = time.time() - self.last_throttle_start_time
        sleep_duration = max(throttle_secs - time_passed, 0.0)
        logger.debug(f"Throttling with '{func.__name__}()': sleep for {sleep_duration:.2f} s, "
                     f"last iteration took {time_passed:.2f} s.")
        time.sleep(sleep_duration)
        return result

    def _process_stopped(self) -> None:
        # self.coingro.process_stopped()

    def _process_running(self) -> None:
        try:
            # self.coingro.process()
        except TemporaryError as error:
            logger.warning(f"Error: {error}, retrying in {RETRY_TIMEOUT} seconds...")
            time.sleep(RETRY_TIMEOUT)
        except (OperationalException, ExchangeError) as error:
            if isinstance(error, OperationalException) or __env__ == 'docker':
                tb = traceback.format_exc()
                hint = 'Issue `/start` if you think it is safe to restart.'

                # self.coingro.notify_status(f'{type(error).__name__}:\n```\n{tb}```{hint}')

                logger.exception(f'{type(error).__name__}. Stopping trader ...')
                # self.coingro.state = State.STOPPED

    def _reconfigure(self) -> None:
        """
        Cleans up current coingrobot instance, reloads the configuration and
        replaces it with the new instance
        """
        # Tell systemd that we initiated reconfiguration
        self._notify("RELOADING=1")

        # Clean up current coingro modules
        # self.coingro.cleanup()

        # Load and validate config and create new instance of the bot
        self._init(True)

        # self.coingro.notify_status('config reloaded')

        # Tell systemd that we completed reconfiguration
        self._notify("READY=1")

    def exit(self) -> None:
        # Tell systemd that we are exiting now
        self._notify("STOPPING=1")

        # if self.coingro:
            # self.coingro.notify_status('process died')
            # self.coingro.cleanup()

