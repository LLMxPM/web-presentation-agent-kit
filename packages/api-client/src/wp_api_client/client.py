"""文件功能：封装 External API v1 的 HTTP 客户端，处理认证、空间隔离、幂等头与任务轮询。"""

from __future__ import annotations

import time
import uuid
from typing import Any, Mapping

import httpx

class ApiClientError(Exception):
    """API 调用异常。"""

    def __init__(
        self,
        message: str,
        status_code: int = 500,
        code: str = "ERROR",
        details: Any = None,
        *,
        request_id: str | None = None,
        retry_after: str | None = None,
    ) -> None:
        """保存结构化错误以及服务端提供的诊断、重试信息。"""

        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.code = code
        self.details = details
        self.request_id = request_id
        self.retry_after = retry_after


class ApiClient:
    """External API v1 交互客户端。"""

    def __init__(
        self,
        endpoint: str,
        token: str | None = None,
        workspace_id: int | None = None,
        user_agent: str = "web-presentation-agent-kit/0.1.0",
        idempotency_key: str | None = None,
    ) -> None:
        """创建客户端；endpoint 不应包含 `/api/v1`，公共前缀由本类统一拼接。"""

        self.endpoint = endpoint.rstrip("/")
        self.token = token
        self.workspace_id = workspace_id
        self.user_agent = user_agent
        self.default_idempotency_key = idempotency_key
        self.client = httpx.Client(base_url=self.endpoint, timeout=30.0)

    def _request(self, method: str, url: str, **kwargs: Any) -> httpx.Response:
        """发送 HTTP 请求并把网络层异常转换为统一的 API Client 错误。"""

        try:
            request_method = getattr(self.client, method.lower())
            return request_method(url, **kwargs)
        except httpx.TimeoutException as exc:
            raise ApiClientError(
                "请求服务端超时，请检查网络或稍后重试。",
                status_code=504,
                code="REQUEST_TIMEOUT",
            ) from exc
        except httpx.RequestError as exc:
            raise ApiClientError(
                f"无法连接服务端：{exc}",
                status_code=503,
                code="NETWORK_ERROR",
            ) from exc

    def _resolve_idempotency_key(self, idempotent: bool, key: str | None) -> str | None:
        """解析本次请求的幂等键；显式参数优先于客户端默认值。"""

        if not idempotent:
            return None
        return key or self.default_idempotency_key or uuid.uuid4().hex

    def _get_headers(
        self,
        *,
        idempotent: bool = False,
        custom_idempotency_key: str | None = None,
        override_workspace_id: int | None = None,
    ) -> dict[str, str]:
        headers: dict[str, str] = {
            "Accept": "application/json",
            "User-Agent": self.user_agent,
        }
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"

        ws_id = override_workspace_id or self.workspace_id
        if ws_id is not None:
            headers["X-Workspace-ID"] = str(ws_id)

        if idempotent:
            headers["Idempotency-Key"] = custom_idempotency_key or uuid.uuid4().hex

        return headers

    def _handle_response(self, response: httpx.Response, *, idempotency_key: str | None = None) -> Any:
        """解析响应，并把请求 ID 与写操作幂等键作为客户端元数据回显。"""

        if response.is_success:
            if response.status_code == 204 or not response.content:
                return {}
            content_type = response.headers.get("content-type", "")
            if "application/json" in content_type:
                try:
                    result = response.json()
                except (TypeError, ValueError):
                    return response.text
                if isinstance(result, dict):
                    metadata = {"request_id": response.headers.get("X-Request-ID")}
                    if idempotency_key:
                        metadata["idempotency_key"] = idempotency_key
                    metadata = {key: value for key, value in metadata.items() if value}
                    if metadata:
                        result["_client"] = metadata
                return result
            return response.text

        # 错误解析
        err_msg = f"HTTP {response.status_code} 请求失败"
        code = "HTTP_ERROR"
        details = None
        try:
            err_json = response.json()
            if isinstance(err_json, dict):
                err_msg = err_json.get("message") or err_json.get("detail") or err_msg
                code = err_json.get("code") or code
                details = err_json.get("data", err_json.get("detail"))
            else:
                details = err_json
        except (TypeError, ValueError):
            err_msg = response.text or err_msg

        raise ApiClientError(
            err_msg,
            status_code=response.status_code,
            code=code,
            details=details,
            request_id=response.headers.get("X-Request-ID"),
            retry_after=response.headers.get("Retry-After"),
        )

    def get(self, path: str, params: Mapping[str, Any] | None = None, workspace_id: int | None = None) -> Any:
        url = f"/api/v1{path}"
        headers = self._get_headers(override_workspace_id=workspace_id)
        resp = self._request("GET", url, params=params, headers=headers)
        return self._handle_response(resp)

    def get_operation_guide(self, operation_key: str | None = None) -> Any:
        """读取 Guides 索引或指定 operation 的版本化详情。"""

        path = "/guides" if operation_key is None else f"/guides/{operation_key}"
        return self.get(path)

    def get_standard(self, entity_type: str) -> dict[str, Any]:
        """读取页面或组件开发标准。"""

        if entity_type not in {"page", "component"}:
            raise ValueError("entity_type 必须为 page 或 component")
        return self.get(f"/standards/{entity_type}")

    def list_runtime_kit(self, params: Mapping[str, Any] | None = None) -> Any:
        """读取 Runtime Kit 能力列表。"""

        return self.get("/runtime-kit", params=params)

    def get_runtime_kit_item(self, item: str) -> dict[str, Any]:
        """读取单个 Runtime Kit 能力。"""

        return self.get(f"/runtime-kit/{item}")

    def list_fonts(self, params: Mapping[str, Any] | None = None) -> Any:
        """读取当前工作空间字体列表。"""

        return self.get("/fonts", params=params)

    def validate_entity(self, payload: Mapping[str, Any]) -> dict[str, Any]:
        """调用页面/组件实体候选内容校验接口。"""

        return self.post("/validate/entity", json_data=dict(payload), idempotent=False)

    def create_page(self, payload: Mapping[str, Any], *, idempotency_key: str | None = None) -> dict[str, Any]:
        """提交页面创建 Mutation Job。"""

        return self.post("/pages", json_data=dict(payload), idempotency_key=idempotency_key)

    def create_component(self, payload: Mapping[str, Any], *, idempotency_key: str | None = None) -> dict[str, Any]:
        """提交组件创建 Mutation Job。"""

        return self.post("/components", json_data=dict(payload), idempotency_key=idempotency_key)

    def copy_page(self, page_id: int, payload: Mapping[str, Any], *, idempotency_key: str | None = None) -> dict[str, Any]:
        """复制页面到目标项目。"""

        return self.post(f"/pages/{page_id}/copy", json_data=dict(payload), idempotency_key=idempotency_key)

    def edit_page(self, page_id: int, payload: Mapping[str, Any], *, idempotency_key: str | None = None) -> dict[str, Any]:
        """提交页面源码编辑 Mutation Job。"""

        return self.post(f"/pages/{page_id}/edits", json_data=dict(payload), idempotency_key=idempotency_key)

    def edit_component(self, component_id: int, payload: Mapping[str, Any], *, idempotency_key: str | None = None) -> dict[str, Any]:
        """提交组件源码编辑 Mutation Job。"""

        return self.post(f"/components/{component_id}/edits", json_data=dict(payload), idempotency_key=idempotency_key)

    def update_component_metadata_async(
        self,
        payload: Mapping[str, Any],
        *,
        idempotency_key: str | None = None,
    ) -> dict[str, Any]:
        """提交组件元数据重校验 Mutation Job。"""

        return self.post("/jobs/mutations/components/metadata", json_data=dict(payload), idempotency_key=idempotency_key)

    def post(
        self,
        path: str,
        json_data: Any | None = None,
        idempotent: bool = True,
        idempotency_key: str | None = None,
        workspace_id: int | None = None,
    ) -> Any:
        url = f"/api/v1{path}"
        resolved_key = self._resolve_idempotency_key(idempotent, idempotency_key)
        headers = self._get_headers(
            idempotent=idempotent,
            custom_idempotency_key=resolved_key,
            override_workspace_id=workspace_id,
        )
        resp = self._request("POST", url, json=json_data, headers=headers)
        return self._handle_response(resp, idempotency_key=resolved_key)

    def patch(
        self,
        path: str,
        json_data: Any | None = None,
        idempotent: bool = True,
        idempotency_key: str | None = None,
        workspace_id: int | None = None,
    ) -> Any:
        url = f"/api/v1{path}"
        resolved_key = self._resolve_idempotency_key(idempotent, idempotency_key)
        headers = self._get_headers(
            idempotent=idempotent,
            custom_idempotency_key=resolved_key,
            override_workspace_id=workspace_id,
        )
        resp = self._request("PATCH", url, json=json_data, headers=headers)
        return self._handle_response(resp, idempotency_key=resolved_key)

    def put(
        self,
        path: str,
        json_data: Any | None = None,
        idempotent: bool = True,
        idempotency_key: str | None = None,
        workspace_id: int | None = None,
    ) -> Any:
        url = f"/api/v1{path}"
        resolved_key = self._resolve_idempotency_key(idempotent, idempotency_key)
        headers = self._get_headers(
            idempotent=idempotent,
            custom_idempotency_key=resolved_key,
            override_workspace_id=workspace_id,
        )
        resp = self._request("PUT", url, json=json_data, headers=headers)
        return self._handle_response(resp, idempotency_key=resolved_key)

    def delete(
        self,
        path: str,
        idempotent: bool = True,
        idempotency_key: str | None = None,
        workspace_id: int | None = None,
    ) -> Any:
        url = f"/api/v1{path}"
        resolved_key = self._resolve_idempotency_key(idempotent, idempotency_key)
        headers = self._get_headers(
            idempotent=idempotent,
            custom_idempotency_key=resolved_key,
            override_workspace_id=workspace_id,
        )
        resp = self._request("DELETE", url, headers=headers)
        return self._handle_response(resp, idempotency_key=resolved_key)

    def upload(
        self,
        path: str,
        files: dict[str, Any],
        data: dict[str, Any] | None = None,
        idempotent: bool = True,
        idempotency_key: str | None = None,
        workspace_id: int | None = None,
    ) -> Any:
        url = f"/api/v1{path}"
        resolved_key = self._resolve_idempotency_key(idempotent, idempotency_key)
        headers = self._get_headers(
            idempotent=idempotent,
            custom_idempotency_key=resolved_key,
            override_workspace_id=workspace_id,
        )
        resp = self._request("POST", url, data=data, files=files, headers=headers)
        return self._handle_response(resp, idempotency_key=resolved_key)

    def poll_mutation_job(
        self,
        job_id: str,
        timeout_seconds: float = 60.0,
        interval: float = 1.0,
    ) -> dict[str, Any]:
        """轮询异步变更任务直到进入终态。"""

        if timeout_seconds <= 0:
            raise ApiClientError("等待 Mutation 任务超时：timeout 必须大于 0。", code="INVALID_TIMEOUT", status_code=400)

        deadline = time.perf_counter() + timeout_seconds
        while time.perf_counter() < deadline:
            job = self.get(f"/jobs/mutations/{job_id}")
            status = job.get("status")
            if status in {"succeeded", "failed", "canceled"}:
                return job
            remaining = deadline - time.perf_counter()
            if remaining > 0:
                time.sleep(min(max(interval, 0), remaining))

        raise ApiClientError(f"等待 Mutation 任务超时 ({timeout_seconds}s)", code="TIMEOUT")

    def get_mutation_job(self, job_id: str) -> dict[str, Any]:
        """查询 Mutation Job。"""

        return self.get(f"/jobs/mutations/{job_id}")

    def cancel_mutation_job(self, job_id: str, *, idempotency_key: str | None = None) -> dict[str, Any]:
        """取消 Mutation Job，并支持调用方复用原幂等键。"""

        return self.post(f"/jobs/mutations/{job_id}/cancel", idempotency_key=idempotency_key)

    def retry_mutation_job(self, job_id: str, *, idempotency_key: str | None = None) -> dict[str, Any]:
        """为可重试失败任务创建一个新 Job。"""

        return self.post(f"/jobs/mutations/{job_id}/retry", idempotency_key=idempotency_key)

    def _is_same_origin(self, target_url: str) -> bool:
        """校验目标 URL 是否与 Client 配置的 API endpoint 同源。"""

        from urllib.parse import urlsplit

        target_parts = urlsplit(target_url)
        endpoint_parts = urlsplit(self.endpoint)
        return (
            target_parts.scheme.lower() == endpoint_parts.scheme.lower()
            and target_parts.netloc.lower() == endpoint_parts.netloc.lower()
        )

    def get_bytes(
        self,
        path_or_url: str,
        params: Mapping[str, Any] | None = None,
        workspace_id: int | None = None,
    ) -> tuple[httpx.Headers, bytes]:
        """获取原始响应 Headers 与二进制 Byte 内容（带有跨域 PAT 泄露防护）。"""

        if path_or_url.startswith("http://") or path_or_url.startswith("https://"):
            if not self._is_same_origin(path_or_url):
                raise ApiClientError(
                    "安全拦截：禁止向非 Endpoint 同源地址发送 PAT 令牌",
                    code="CROSS_ORIGIN_PAT_BLOCKED",
                )
            url = path_or_url
        elif path_or_url.startswith("/api/v1"):
            url = path_or_url
        else:
            url = f"/api/v1{path_or_url}" if path_or_url.startswith("/") else f"/api/v1/{path_or_url}"

        headers = self._get_headers(override_workspace_id=workspace_id)
        resp = self._request("GET", url, params=params, headers=headers)
        if not resp.is_success:
            self._handle_response(resp)
        return resp.headers, resp.content

    def get_latest_page_screenshot(self, page_id: int) -> tuple[dict[str, Any], bytes]:
        """请求 External API v1 获取最新 PNG 截图 (一次性 GET 请求)。"""

        resp_headers, img_bytes = self.get_bytes(f"/pages/{page_id}/screenshot")
        content_type = str(resp_headers.get("content-type") or "").split(";", 1)[0].strip().lower()
        if "image/png" not in content_type:
            raise ApiClientError(
                f"服务端响应 Content-Type 异常 ('{content_type}')，预期为 image/png",
                code="INVALID_CONTENT_TYPE",
            )

        version_no_str = resp_headers.get("x-page-version-no")
        if not version_no_str:
            raise ApiClientError(
                "服务端未返回有效的页面版本响应头 (X-Page-Version-No)",
                code="INVALID_HEADER",
            )

        try:
            version_no = int(version_no_str)
        except ValueError as exc:
            raise ApiClientError(
                f"服务端返回的页面版本响应头格式非法 ('{version_no_str}')",
                code="INVALID_HEADER",
            ) from exc

        meta = {
            "page_id": page_id,
            "version_no": version_no,
        }
        return meta, img_bytes

    def close(self) -> None:
        """关闭底层 HTTP 连接池。"""

        self.client.close()

    def __enter__(self) -> "ApiClient":
        return self

    def __exit__(self, exc_type: Any, exc_value: Any, traceback: Any) -> None:
        self.close()
