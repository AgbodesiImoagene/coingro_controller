import logging
from typing import Any, Dict, List, Optional

from coingro.exceptions import TemporaryError
from coingro.misc import retrier
from kubernetes import client
from kubernetes import config as k8s_config

from coingro_controller.k8s.resources import Resources


logger = logging.getLogger(__name__)


class Client:
    def __init__(self, config: Dict[str, Any]):
        self._config = config
        self.resources = Resources(config)
        self.namespace = self.resources.namespace

        k8s_config.load_incluster_config()
        self.core_api = client.CoreV1Api()

    def get_coingro_instance(self, name: str) -> Dict[str, Any]:
        return self.core_api.read_namespaced_pod(name, self.namespace)

    def get_coingro_instances(self) -> List[Any]:
        res = self.core_api.list_namespaced_pod(self.namespace)
        items = res['items'] if 'items' in res else []
        return items

    def create_coingro_instance(self,
                                name: str,
                                create_pvc: bool = False,
                                env_vars: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        try:
            if create_pvc:
                self._create_coingro_data_pvc(name)
            self._create_coingro_service(name)
            cg_pod = self._create_coingro_pod(name, env_vars)
            return cg_pod
        except Exception as e:
            logger.error(f"Could not create coingro instance {name} due to {e}.")
            return {}

    @retrier(retries=3, sleep_time=1)
    def _create_coingro_data_pvc(self, name: str) -> Dict[str, Any]:
        cg_pvc = self.resources.get_coingro_user_data_pvc(name)
        try:
            return self.core_api.create_namespaced_persistent_volume_claim(self.namespace, cg_pvc)
        except Exception as e:  # Get specific exceptions
            raise TemporaryError(e)

    @retrier(retries=3, sleep_time=1)
    def _create_coingro_service(self, name: str) -> Dict[str, Any]:
        cg_service = self.resources.get_coingro_service(name)
        try:
            return self.core_api.create_namespaced_service(self.namespace, cg_service)
        except Exception as e:  # Get specific exceptions
            raise TemporaryError(e)

    @retrier(retries=3, sleep_time=1)
    def _create_coingro_pod(self,
                            name: str,
                            env_vars: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        cg_pod = self.resources.get_coingro_pod(name, env_vars)
        try:
            return self.core_api.create_namespaced_pod(self.namespace, cg_pod)
        except Exception as e:  # Get specific exceptions
            raise TemporaryError(e)

    # def update_coingro_instance(self, name: str) -> Dict[str, Any]:
    #   cg_pod = self._update_coingro_pod(name)
    #   return cg_pod

    # @retrier(retries=3, sleep_time=1)
    # def _update_coingro_pod(self, name: str) -> Dict[str, Any]:
    #   cg_pod = self.resources.get_coingro_pod(name)
    #   try:
    #       return self.core_api.replace_namespaced_pod(name, self.namespace, cg_pod)
    #   except Exception as e: # Get specific exceptions
    #       raise TemporaryError(e)

    def delete_coingro_instance(self, name: str, delete_pvc: bool = False) -> Dict[str, Any]:
        try:
            cg_pod = self._delete_coingro_pod(name)
            self._delete_coingro_service(name)
            if delete_pvc:
                self._delete_coingro_data_pvc(name)
            return cg_pod
        except Exception as e:
            logger.error(f"Could not delete coingro instance {name} due to {e}.")
            return {}

    @retrier(retries=3, sleep_time=1)
    def _delete_coingro_data_pvc(self, name: str) -> Dict[str, Any]:
        try:
            return self.core_api.delete_namespaced_persistent_volume_claim(name, self.namespace)
        except Exception as e:  # Get specific exceptions
            raise TemporaryError(e)

    @retrier(retries=3, sleep_time=1)
    def _delete_coingro_service(self, name: str) -> Dict[str, Any]:
        try:
            return self.core_api.delete_namespaced_service(name, self.namespace)
        except Exception as e:  # Get specific exceptions
            raise TemporaryError(e)

    @retrier(retries=3, sleep_time=1)
    def _delete_coingro_pod(self, name: str) -> Dict[str, Any]:
        try:
            return self.core_api.delete_namespaced_pod(name, self.namespace)
        except Exception as e:  # Get specific exceptions
            raise TemporaryError(e)
