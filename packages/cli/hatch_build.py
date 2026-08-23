"""文件功能：为 CLI 的 editable 安装映射共享 API Client 源码。"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from hatchling.builders.hooks.plugin.interface import BuildHookInterface


class CustomBuildHook(BuildHookInterface):
    """在本地 editable 构建时，把同仓 API Client 映射到 CLI 环境。"""

    def initialize(self, version: str, build_data: dict[str, Any]) -> None:
        """为 editable wheel 注入跨目录 API Client，正式发行包沿用标准打包配置。"""

        if version != "editable":
            return

        api_client_source = Path(self.root).parent / "api-client" / "src" / "wp_api_client"
        build_data["force_include_editable"] = {str(api_client_source): "wp_api_client"}
