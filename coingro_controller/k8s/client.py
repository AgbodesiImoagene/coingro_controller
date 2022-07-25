from typing import Any, Dict, List, Optional

from kubernetes import client
from kubernetes import config as k8s_config

from coingro.exceptions import TemporaryError
from coingro.misc import retrier

from coingro_controller.constants import DEFAULT_NAMESPACE
from coingro_controller.k8s.resources import Resources
from coingro_controller.misc import generate_uid
from coingro_controller.persistence import Bot


logger = logging.getLogger(__name__)


class Client:
	def __init__(self, config: Dict[str, Any]):
		self._config = config
		self.resources = Resources(config)
		self.namespace = self.resources.namespace

	    k8s_config.load_incluster_config()
		self.core_api = client.CoreV1Api()

		self._init_namespace()

	@retrier(retries=3, sleep_time=10)
	def _init_namespace(self):
		res = self.core_api.list_namespace()
		items = res['items'] if 'items' in res else []
		namespaces = [ns_data['name'] for ns_data in items in 'name' in ns_data]
		if self.namespace not in namespaces:
			try:
				namespace_object = self.resources.get_namespace_object()
				self.core_api.create_namespace(namespace_object)
			except Exception as e: # Get specific exceptions
				raise TemporaryError(e)

	def get_coingro_instance(self, name: str) -> Dict[str, Any]:
		return self.core_api.read_namespaced_pod(name, self.namespace)

	def get_coingro_instances(self) -> List[Any]:
		res = self.core_api.list_namespaced_pod(self.namespace)
		items = res['items'] if 'items' in res else []
		return items

	def create_coingro_instance(self,
								name: str,
								env_vars: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
		_ = self._create_coingro_service(name)
		cg_pod = self._create_coingro_pod(name, env_vars)
		return cg_pod

	@retrier(retries=3, sleep_time=1)
	def _create_coingro_service(self, name: str) -> Dict[str, Any]:
		cg_service = self.resources.get_coingro_service(name)
		try:
			return self.core_api.create_namespaced_service(self.namespace, cg_service)
		except Exception as e: # Get specific exceptions
			raise TemporaryError(e)

	@retrier(retries=3, sleep_time=1)
	def _create_coingro_pod(self,
							name: str,
							env_vars: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
		cg_pod = self.resources.get_coingro_pod(name, env_vars)
		try:
			return self.core_api.create_namespaced_pod(self.namespace, cg_pod)
		except Exception as e: # Get specific exceptions
			raise TemporaryError(e)

	# def update_coingro_instance(self, name: str) -> Dict[str, Any]:
	# 	cg_pod = self._update_coingro_pod(name)
	# 	return cg_pod

	# @retrier(retries=3, sleep_time=1)
	# def _update_coingro_pod(self, name: str) -> Dict[str, Any]:
	# 	cg_pod = self.resources.get_coingro_pod(name)
	# 	try:
	# 		return self.core_api.replace_namespaced_pod(name, self.namespace, cg_pod)
	# 	except Exception as e: # Get specific exceptions
	# 		raise TemporaryError(e)

	def delete_coingro_instance(self, name: str) -> Dict[str, Any]:
		cg_pod = self._delete_coingro_pod(name)
		_ = self._delete_coingro_service(name)
		return cg_pod

	@retrier(retries=3, sleep_time=1)
	def _delete_coingro_service(self, name: str) -> Dict[str, Any]:
		try:
			return self.core_api.delete_namespaced_service(name, self.namespace)
		except Exception as e: # Get specific exceptions
			raise TemporaryError(e)

	@retrier(retries=3, sleep_time=1)
	def _delete_coingro_pod(self, name: str) -> Dict[str, Any]:
		try:
			return self.core_api.delete_namespaced_pod(name, self.namespace)
		except Exception as e: # Get specific exceptions
			raise TemporaryError(e)
