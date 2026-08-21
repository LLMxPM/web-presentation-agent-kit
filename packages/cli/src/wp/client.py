"""文件功能：提供 CLI 对共享 External API v1 客户端的 Profile 适配。"""

from __future__ import annotations

from wp.config import ProfileConfig
from wp_api_client import ApiClient as SharedApiClient, ApiClientError


class ApiClient(SharedApiClient):
    """把 CLI ProfileConfig 适配为共享 API Client。"""

    def __init__(self, profile: ProfileConfig, workspace_id: int | None = None) -> None:
        super().__init__(
            endpoint=profile.endpoint,
            token=profile.token,
            workspace_id=workspace_id or profile.default_workspace_id,
            user_agent="web-presentation-cli/0.1.0",
        )


__all__ = ["ApiClient", "ApiClientError"]
