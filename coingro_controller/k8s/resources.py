import logging
from typing import Any, Dict, Optional

from kubernetes import client

from coingro_controller.constants import DEFAULT_NAMESPACE


logger = logging.getLogger(__name__)


class Resources:
    def __init__(self, config: Dict[str, Any]):
        self._config = config
        self.namespace = str(self._config.get('namespace', DEFAULT_NAMESPACE))
        self.cg_port = self._config['cg_api_server_port']

    def get_namespace_object(self) -> client.V1Namespace:
        meta = client.V1ObjectMeta()
        meta.name = self.namespace
        meta.labels = {'name': self.namespace, 'creator': 'coingro-controller'}

        cg_namespace = client.V1Namespace()
        cg_namespace.api_version = 'v1'
        cg_namespace.kind = 'Namespace'
        cg_namespace.metadata = meta
        return cg_namespace

    def get_coingro_user_data_pvc(self, name: str) -> client.V1Service:
        meta = client.V1ObjectMeta()
        meta.name = name
        meta.namespace = self.namespace
        meta.labels = {
            'name': f'{name}-user-data-pvc',
            'mount': '/coingro/user_data',
            'app': 'coingro-bot',
            'creator': 'coingro-controller'
        }

        resources = client.V1ResourceRequirements()
        resources.requests = {'storage': '500Mi'}

        spec = client.V1PersistentVolumeClaimSpec()
        spec.access_modes = ['ReadWriteOnce']
        spec.resources = resources

        pvc = client.V1PersistentVolumeClaim()
        pvc.metadata = meta
        pvc.spec = spec

        return pvc

    def get_coingro_service(self, name: str) -> client.V1Service:
        meta = client.V1ObjectMeta()
        meta.name = name
        meta.namespace = self.namespace
        meta.labels = {
            'name': name,
            'run': name,
            'app': 'coingro-bot',
            'creator': 'coingro-controller'
        }

        cg_api_server_port = client.V1ServicePort()
        cg_api_server_port.name = 'api-server-port'
        cg_api_server_port.protocol = 'TCP'
        cg_api_server_port.port = 8080
        cg_api_server_port.target_port = self.cg_port

        spec = client.V1ServiceSpec()
        spec.selectors = {
            'run': name,
            'creator': 'coingro-controller'
        }
        spec.ports = [cg_api_server_port]

        cg_service = client.V1Service()
        cg_service.api_version = 'v1'
        cg_service.kind = 'Service'
        cg_service.metadata = meta
        cg_service.spec = spec

        return cg_service

    def get_coingro_pod(self, name: str,
                        env_vars: Optional[Dict[str, Any]] = None) -> client.V1Pod:
        env = self._config.get('cg_env_vars', {})
        if env_vars:
            env.update(env_vars)
        env_list = []

        if env:
            for key, val in env:
                env_list.append(client.V1EnvVar(name=str(key), value=str(val)))

        env_list.append(client.V1EnvVar(name='CG_BOT_ID', value=name))

        startup_action = client.V1HTTPGetAction(path='api/v1/ping')
        startup_action.port = self.cg_port
        startup_probe = client.V1Probe()
        startup_probe.http_get = startup_action
        startup_probe.failure_threshold = 10
        startup_probe.period_seconds = 3

        liveness_action = client.V1HTTPGetAction(path='api/v1/ping')
        liveness_action.port = self.cg_port
        liveness_probe = client.V1Probe()
        liveness_probe.http_get = liveness_action
        liveness_probe.failure_threshold = 1
        liveness_probe.period_seconds = 60

        data_mount = client.V1VolumeMount()
        data_mount.mount_path = '/coingro/user_data/'
        data_mount.name = f'{name}-user-data'

        strategies_mount = client.V1VolumeMount()
        strategies_mount.mount_path = '/coingro/strategies/'
        strategies_mount.name = f'{name}-strategies'

        data_pvc_claim_source = client.V1PersistentVolumeClaimVolumeSource()
        data_pvc_claim_source.claim_name = f'{name}-user-data-pvc'

        strategies_pvc_claim_source = client.V1PersistentVolumeClaimVolumeSource()
        strategies_pvc_claim_source.claim_name = \
            self._config.get('cg_strategies_pvc_claim', 'strategies-pvc')

        cg_data_volume = client.V1Volume()
        cg_data_volume.persistent_volume_claim = data_pvc_claim_source

        cg_strategies_volume = client.V1Volume()
        cg_strategies_volume.persistent_volume_claim = strategies_pvc_claim_source

        cg_api_server_port = client.V1ContainerPort()
        cg_api_server_port.name = 'api-server-port'
        cg_api_server_port.container_port = self.cg_port

        cg_container = client.V1Container()
        cg_container.name = 'coingro-container'
        cg_container.image = self._config['cg_image']
        cg_container.env = env_list
        cg_container.liveness_probe = liveness_probe
        cg_container.startup_probe = startup_probe
        cg_container.volume_mount = [data_mount, strategies_mount]
        cg_container.ports = [cg_api_server_port]

        meta = client.V1ObjectMeta()
        meta.name = name
        meta.namespace = self.namespace
        meta.labels = {
            'name': name,
            'run': name,
            'app': 'coingro-bot',
            'creator': 'coingro-controller'
        }

        spec = client.V1PodSpec()
        spec.containers = [cg_container]
        spec.volumes = [cg_data_volume, cg_strategies_volume]

        cg_pod = client.V1Pod()
        cg_pod.api_version = 'v1'
        cg_pod.kind = 'Pod'
        cg_pod.metadata = meta
        cg_pod.spec = spec

        return cg_pod
