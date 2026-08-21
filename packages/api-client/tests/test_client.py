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
