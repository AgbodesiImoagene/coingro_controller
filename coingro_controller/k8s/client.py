import logging
from typing import Any, Dict, List, Optional

from kubernetes import client
from kubernetes import config as k8s_config

from coingro.exceptions import TemporaryError  # , OperationalException
from coingro.misc import retrier
from coingro_controller.k8s.resources import Resources

logger = logging.getLogger(__name__)


class Client:
    def __init__(self, config: Dict[str, Any]):
        self._config = config
        self.resources = Resources(config)
        self.namespace = self.resources.namespace

        k8s_config.load_incluster_config()
        self.core_api = client.CoreV1Api()

    def get_coingro_instance(self, bot_id: str):
        try:
            return self.core_api.read_namespaced_pod(bot_id, self.namespace)
        except Exception as e:
            logger.error(f"Kubernetes client error: {e}")
            return None

    def _get_coingro_service(self, bot_id: str):
        try:
            return self.core_api.read_namespaced_service(bot_id, self.namespace)
        except Exception as e:
            logger.error(f"Kubernetes client error: {e}")
            return None

    def get_coingro_instances(self) -> List[Any]:
        res = self.core_api.list_namespaced_pod(self.namespace)
        items = res.items if res else []
        return items

    def create_coingro_instance(
        self, bot_id: str, config: Dict[str, Any], env_vars: Optional[Dict[str, Any]] = None
    ):
        try:
            self._create_coingro_service(bot_id)
            cg_pod = self._create_coingro_pod(bot_id, config, env_vars)
            return cg_pod
        except Exception as e:
            logger.error(f"Could not create coingro instance {bot_id} due to: {e}.")
            # raise OperationalException(e)

    @retrier(retries=3, sleep_time=1)
    def _create_coingro_data_pvc(self, bot_id: str):
        cg_pvc = self.resources.get_coingro_user_data_pvc(bot_id)
        try:
            return self.core_api.create_namespaced_persistent_volume_claim(self.namespace, cg_pvc)
        except Exception as e:  # Get specific exceptions
            raise TemporaryError(f"error {e} creating persistent volume claim")

    @retrier(retries=3, sleep_time=1)
    def _create_coingro_service(self, bot_id: str):
        cg_service = self.resources.get_coingro_service(bot_id)
        try:
            service = self._get_coingro_service(bot_id)
            if not service:
                service = self.core_api.create_namespaced_service(self.namespace, cg_service)
            return service
        except Exception as e:  # Get specific exceptions
            raise TemporaryError(f"error {e} creating service")

    @retrier(retries=3, sleep_time=1)
    def _create_coingro_pod(
        self, bot_id: str, config: Dict[str, Any], env_vars: Optional[Dict[str, Any]] = None
    ):
        cg_pod = self.resources.get_coingro_pod(bot_id, config, env_vars)
        try:
            pod = self.get_coingro_instance(bot_id)
            if pod:
                self._delete_coingro_pod(bot_id)
            return self.core_api.create_namespaced_pod(self.namespace, cg_pod)
        except Exception as e:  # Get specific exceptions
            raise TemporaryError(f"error {e} creating pod")

    def delete_coingro_instance(self, bot_id: str):
        try:
            cg_pod = self._delete_coingro_pod(bot_id)
            self._delete_coingro_service(bot_id)
            return cg_pod
        except Exception as e:
            logger.error(f"Could not delete coingro instance {bot_id} due to: {e}.")
            # raise OperationalException(e)

    @retrier(retries=3, sleep_time=1)
    def _delete_coingro_data_pvc(self, bot_id: str):
        try:
            return self.core_api.delete_namespaced_persistent_volume_claim(bot_id, self.namespace)
        except Exception as e:  # Get specific exceptions
            raise TemporaryError(f"error {e} deleting persistent volume claim")

    @retrier(retries=3, sleep_time=1)
    def _delete_coingro_service(self, bot_id: str):
        try:
            service = self._get_coingro_service(bot_id)
            if service:
                self.core_api.delete_namespaced_service(bot_id, self.namespace)
            return service
        except Exception as e:  # Get specific exceptions
            raise TemporaryError(f"error {e} deleting service")

    @retrier(retries=3, sleep_time=1)
    def _delete_coingro_pod(self, bot_id: str):
        try:
            # pod = self.get_coingro_instance(bot_id)
            # if pod:
            return self.core_api.delete_namespaced_pod(bot_id, self.namespace)
            # return pod
        except Exception as e:  # Get specific exceptions
            raise TemporaryError(f"error {e} deleting pod")

    def replace_coingro_instance(
        self, bot_id: str, config: Dict[str, Any], env_vars: Optional[Dict[str, Any]] = None
    ):
        try:
            cg_pod = self._replace_coingro_pod(bot_id, config, env_vars)
            return cg_pod
        except Exception as e:
            logger.error(f"Could not replace coingro instance {bot_id} due to: {e}.")
            # raise OperationalException(e)

    @retrier(retries=3, sleep_time=1)
    def _replace_coingro_pod(
        self, bot_id: str, config: Dict[str, Any], env_vars: Optional[Dict[str, Any]] = None
    ):
        cg_pod = self.resources.get_coingro_pod(bot_id, config, env_vars)
        try:
            return self.core_api.replace_namespaced_pod(bot_id, self.namespace, cg_pod)
        except Exception as e:  # Get specific exceptions
            raise TemporaryError(f"error {e} deleting pod")
