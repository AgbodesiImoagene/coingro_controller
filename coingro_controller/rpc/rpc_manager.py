"""
This module contains class to manage RPC communications (Telegram, API, ...)
"""
import logging
from typing import List

from coingro.rpc import RPCHandler

from coingro_controller.rpc import RPC


logger = logging.getLogger(__name__)


class RPCManager:
    """
    Class to manage RPC objects (Telegram, API, ...)
    """

    def __init__(self, controller) -> None:
        """ Initializes all enabled rpc modules """
        self.registered_modules: List[RPCHandler] = []
        self._rpc = RPC(controller)
        config = controller.config

        # Enable local rest api server for cmd line control
        if config.get('api_server', {}).get('enabled', False):
            logger.info('Enabling rpc.api_server')
            from coingro_controller.rpc.api_server import ApiServer
            apiserver = ApiServer(config)
            apiserver.add_rpc_handler(self._rpc)
            self.registered_modules.append(apiserver)

    def cleanup(self) -> None:
        """ Stops all enabled rpc modules """
        logger.info('Cleaning up rpc modules ...')
        while self.registered_modules:
            mod = self.registered_modules.pop()
            logger.info('Cleaning up rpc.%s ...', mod.name)
            mod.cleanup()
            del mod
