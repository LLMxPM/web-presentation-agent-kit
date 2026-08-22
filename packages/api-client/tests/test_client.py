"""文件功能：验证共享 API Client 的 External API v1 路径、认证和安全边界。"""

from unittest.mock import Mock

import httpx
import pytest

from wp_api_client import ApiClient, ApiClientError


def test_client_uses_external_api_v1_and_workspace_headers() -> None:
    client = ApiClient(
        endpoint="http://backend.test/",
        token="pat_secret",
        workspace_id=12,
    )
    response = Mock(spec=httpx.Response)
    response.is_success = True
    response.status_code = 200
    response.content = b'{"items": []}'
    response.headers = {"content-type": "application/json"}
    response.json.return_value = {"items": []}
    client.client.get = Mock(return_value=response)

    assert client.get("/workspaces") == {"items": []}
    request = client.client.get.call_args
    assert request.args[0] == "/api/v1/workspaces"
    assert request.kwargs["headers"]["Authorization"] == "Bearer pat_secret"
    assert request.kwargs["headers"]["X-Workspace-ID"] == "12"
    client.close()


def test_client_blocks_cross_origin_download_with_pat() -> None:
    client = ApiClient("https://backend.test", token="pat_secret")

    with pytest.raises(ApiClientError, match="安全拦截"):
        client.get_bytes("https://evil.test/private.png")

    client.close()


def test_mutation_cancel_replays_key_and_accepts_202() -> None:
    """验证取消请求路径、幂等键回显、request ID 与 202 running 响应。"""

    captured: dict[str, str] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["path"] = request.url.path
        captured["key"] = request.headers["Idempotency-Key"]
        return httpx.Response(
            202,
            json={"job_id": "job-1", "status": "running"},
            headers={"X-Request-ID": "req-1"},
        )

    client = ApiClient("https://backend.test", token="pat_secret", workspace_id=12)
    client.client.close()
    client.client = httpx.Client(base_url=client.endpoint, transport=httpx.MockTransport(handler))
    result = client.cancel_mutation_job("job-1", idempotency_key="cancel-key-1")

    assert captured == {"path": "/api/v1/jobs/mutations/job-1/cancel", "key": "cancel-key-1"}
    assert result["status"] == "running"
    assert result["_client"] == {"request_id": "req-1", "idempotency_key": "cancel-key-1"}
    client.close()


def test_retry_after_and_request_id_are_preserved_on_conflict() -> None:
    """验证客户端保留服务端幂等并发冲突的重试提示。"""

    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(
            409,
            json={"code": "CONCURRENT_MUTATION_IN_PROGRESS", "message": "稍后重试", "data": {"retryable": True}},
            headers={"Retry-After": "1", "X-Request-ID": "req-conflict"},
        )

    client = ApiClient("https://backend.test", token="pat_secret")
    client.client.close()
    client.client = httpx.Client(base_url=client.endpoint, transport=httpx.MockTransport(handler))

    with pytest.raises(ApiClientError) as caught:
        client.retry_mutation_job("job-failed", idempotency_key="retry-key")
    assert caught.value.retry_after == "1"
    assert caught.value.request_id == "req-conflict"
    assert caught.value.details == {"retryable": True}
    client.close()


def test_guides_detail_and_pending_poll_paths(monkeypatch) -> None:
    """验证 Guides 详情路径以及 pending/running 轮询到终态。"""

    statuses = iter(["pending", "running", "succeeded"])
    paths: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        paths.append(request.url.path)
        if request.url.path.endswith("/guides/page.update"):
            return httpx.Response(200, json={"operation_key": "page.update"})
        return httpx.Response(200, json={"job_id": "job-1", "status": next(statuses)})

    monkeypatch.setattr("wp_api_client.client.time.sleep", lambda _: None)
    client = ApiClient("https://backend.test", token="pat_secret")
    client.client.close()
    client.client = httpx.Client(base_url=client.endpoint, transport=httpx.MockTransport(handler))

    assert client.get_operation_guide("page.update")["operation_key"] == "page.update"
    assert client.poll_mutation_job("job-1", interval=0)["status"] == "succeeded"
    assert paths == [
        "/api/v1/guides/page.update",
        "/api/v1/jobs/mutations/job-1",
        "/api/v1/jobs/mutations/job-1",
        "/api/v1/jobs/mutations/job-1",
    ]
    client.close()
