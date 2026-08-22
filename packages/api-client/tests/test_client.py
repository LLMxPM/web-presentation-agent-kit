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


def test_typed_capability_helpers_use_canonical_external_paths() -> None:
    """验证新增 typed helper 不绕过 /api/v1 且保持请求体结构。"""

    paths: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        paths.append(request.url.path)
        return httpx.Response(200, json={"ok": True})

    client = ApiClient("https://backend.test", token="pat_secret", workspace_id=9)
    client.client.close()
    client.client = httpx.Client(base_url=client.endpoint, transport=httpx.MockTransport(handler))

    assert client.get_standard("page")["ok"] is True
    assert client.list_runtime_kit()["ok"] is True
    assert client.get_runtime_kit_item("Export.v1")["ok"] is True
    assert client.list_fonts()["ok"] is True
    assert client.validate_entity({"entity_type": "page", "entity_id": 1, "mode": "current"})["ok"] is True
    assert client.copy_page(1, {"target_project_id": 2})["ok"] is True
    assert client.create_component({"workspace_id": 9, "name": "Card"})["ok"] is True
    assert client.update_component_metadata_async({"component_id": 3, "name": "Card"})["ok"] is True

    assert paths == [
        "/api/v1/standards/page",
        "/api/v1/runtime-kit",
        "/api/v1/runtime-kit/Export.v1",
        "/api/v1/fonts",
        "/api/v1/validate/entity",
        "/api/v1/pages/1/copy",
        "/api/v1/components",
        "/api/v1/jobs/mutations/components/metadata",
    ]
    client.close()


def test_client_reuses_default_idempotency_key_for_write_requests() -> None:
    """验证调用方提供的默认幂等键会进入所有写请求。"""

    captured: dict[str, str] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["key"] = request.headers["Idempotency-Key"]
        return httpx.Response(200, json={"ok": True})

    client = ApiClient("https://backend.test", token="pat_secret", idempotency_key="replay-key")
    client.client.close()
    client.client = httpx.Client(base_url=client.endpoint, transport=httpx.MockTransport(handler))

    assert client.patch("/projects/1", json_data={"name": "项目"})["ok"] is True
    assert captured["key"] == "replay-key"
    client.close()


def test_client_preserves_validation_detail_and_handles_non_object_error() -> None:
    """验证 422 detail 不丢失，并避免非对象错误体触发 AttributeError。"""

    responses = iter(
        [
            httpx.Response(
                422,
                json={"code": "VALIDATION_ERROR", "message": "参数错误", "detail": [{"loc": ["body", "name"]}]},
            ),
            httpx.Response(400, json=["bad request"]),
        ]
    )
    client = ApiClient("https://backend.test", token="pat_secret")
    client.client.close()
    client.client = httpx.Client(
        base_url=client.endpoint,
        transport=httpx.MockTransport(lambda _: next(responses)),
    )

    with pytest.raises(ApiClientError) as validation_error:
        client.get("/projects")
    assert validation_error.value.details == [{"loc": ["body", "name"]}]

    with pytest.raises(ApiClientError) as list_error:
        client.get("/projects")
    assert list_error.value.details == ["bad request"]
    client.close()


def test_client_wraps_transport_errors() -> None:
    """验证连接失败统一转换为稳定的网络错误码。"""

    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("offline", request=request)

    client = ApiClient("https://backend.test", token="pat_secret")
    client.client.close()
    client.client = httpx.Client(base_url=client.endpoint, transport=httpx.MockTransport(handler))

    with pytest.raises(ApiClientError) as caught:
        client.get("/workspaces")
    assert caught.value.code == "NETWORK_ERROR"
    assert caught.value.status_code == 503
    client.close()
