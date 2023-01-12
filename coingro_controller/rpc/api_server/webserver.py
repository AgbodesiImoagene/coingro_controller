import logging
from typing import Any, Dict

import uvicorn
from fastapi import FastAPI

# from fastapi.exception_handlers import http_exception_handler
from fastapi.middleware.cors import CORSMiddleware

# from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.responses import JSONResponse

from coingro.exceptions import OperationalException
from coingro.rpc.api_server.uvicorn_threaded import UvicornServer
from coingro.rpc.api_server.webserver import CGJSONResponse
from coingro.rpc.rpc import RPCException, RPCHandler
from coingro_controller.rpc.rpc import RPC

logger = logging.getLogger(__name__)


app = FastAPI()


class ApiServer(RPCHandler):

    __instance = None
    __initialized = False

    _rpc: RPC
    # Backtesting type: Backtesting
    _bt = None
    _bt_data = None
    _bt_timerange = None
    _bt_last_config: Dict[str, Any] = {}
    _has_rpc: bool = False
    _bgtask_running: bool = False
    _config: Dict[str, Any] = {}
    # Exchange - only available in webserver mode.
    _exchange = None

    def __new__(cls, *args, **kwargs):
        """
        This class is a singleton.
        We'll only have one instance of it around.
        """
        if ApiServer.__instance is None:
            ApiServer.__instance = object.__new__(cls)
            ApiServer.__initialized = False
        return ApiServer.__instance

    def __init__(self, config: Dict[str, Any], standalone: bool = False) -> None:
        ApiServer._config = config
        if self.__initialized and (standalone or self._standalone):
            return
        self._standalone: bool = standalone
        self._server = None
        ApiServer.__initialized = True

        api_config = self._config["api_server"]

        self.app = FastAPI(
            title="Coingro API",
            docs_url="/docs" if api_config.get("enable_openapi", False) else None,
            redoc_url="/redoc" if api_config.get("enable_openapi", False) else None,
            default_response_class=CGJSONResponse,
        )
        self.configure_app(self.app, self._config)

        self.start_api()

    def add_rpc_handler(self, rpc: RPC):
        """
        Attach rpc handler
        """
        if not self._has_rpc:
            ApiServer._rpc = rpc
            ApiServer._has_rpc = True
        else:
            # This should not happen assuming we didn't mess up.
            raise OperationalException("RPC Handler already attached.")

    def cleanup(self) -> None:
        """Cleanup pending module resources"""
        ApiServer._has_rpc = False
        del ApiServer._rpc
        if self._server and not self._standalone:
            logger.info("Stopping API Server")
            self._server.cleanup()

    @classmethod
    def shutdown(cls):
        cls.__initialized = False
        del cls.__instance
        cls.__instance = None
        cls._has_rpc = False
        cls._rpc = None

    def send_msg(self, msg: Dict[str, str]) -> None:
        pass

    def handle_rpc_exception(self, request, exc):
        logger.exception(f"API Error calling: {exc}")
        return JSONResponse(
            status_code=502, content={"error": f"Error querying {request.url.path}: {exc.message}"}
        )

    # def custom_http_exception_handler(self, request, exc):
    #     logger.exception({'error': f"API error querying {request.url.path}: {repr(exc)}"})
    #     return http_exception_handler(request, exc)

    def configure_app(self, app: FastAPI, config):
        from coingro_controller.rpc.api_server.api_v1 import router as api_v1

        app.include_router(
            api_v1,
            prefix="/api/v1",
        )

        app.add_middleware(
            CORSMiddleware,
            allow_origins=config["api_server"].get("CORS_origins", []),
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

        app.add_exception_handler(RPCException, self.handle_rpc_exception)
        # app.add_exception_handler(StarletteHTTPException, self.custom_http_exception_handler)

    def start_api(self):
        """
        Start API ... should be run in thread.
        """
        rest_ip = self._config["api_server"]["listen_ip_address"]
        rest_port = self._config["api_server"]["listen_port"]

        logger.info(f"Starting HTTP Server at {rest_ip}:{rest_port}")
        verbosity = self._config["api_server"].get("verbosity", "error")

        uvconfig = uvicorn.Config(
            self.app,
            port=rest_port,
            host=rest_ip,
            use_colors=False,
            log_config=None,
            access_log=True if verbosity != "error" else False,
        )
        try:
            self._server = UvicornServer(uvconfig)
            if self._standalone:
                self._server.run()
            else:
                self._server.run_in_thread()
        except Exception:
            logger.exception("Api server failed to start.")
