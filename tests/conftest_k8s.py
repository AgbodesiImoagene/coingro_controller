from kubernetes import client


def mock_pod(name: str, state: str = "Running") -> client.V1Pod:
    cg_container = client.V1Container(name="coingro-container")

    meta = client.V1ObjectMeta()
    meta.name = name
    meta.labels = {
        "name": name,
        "run": name,
        "app": "coingro-bot",
        "creator": "coingro-controller",
    }

    spec = client.V1PodSpec(containers=[cg_container])

    status = client.V1PodStatus(phase=state)

    cg_pod = client.V1Pod()
    cg_pod.api_version = "v1"
    cg_pod.kind = "Pod"
    cg_pod.metadata = meta
    cg_pod.spec = spec
    cg_pod.status = status

    return cg_pod
