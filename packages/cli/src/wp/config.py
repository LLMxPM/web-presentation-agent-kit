"""文件功能：管理 CLI 本地配置文件与多 Profile 切换（存储在 ~/.web-presentation/config.json）。"""

from __future__ import annotations

import json
import os
from pathlib import Path
import tempfile
import time

from pydantic import BaseModel, Field, ValidationError

CONFIG_DIR = Path.home() / ".web-presentation"
CONFIG_FILE = CONFIG_DIR / "config.json"
DEFAULT_PROFILE = "default"
DEFAULT_ENDPOINT = "http://127.0.0.1:8000"


class ProfileConfig(BaseModel):
    """单个环境 Profile 配置项。"""

    endpoint: str = Field(default=DEFAULT_ENDPOINT)
    token: str | None = Field(default=None)
    default_workspace_id: int | None = Field(default=None)


class CliConfig(BaseModel):
    """CLI 全局配置文件。"""

    current_profile: str = Field(default=DEFAULT_PROFILE)
    profiles: dict[str, ProfileConfig] = Field(
        default_factory=lambda: {DEFAULT_PROFILE: ProfileConfig()}
    )


def load_config() -> CliConfig:
    """加载本地配置文件；若不存在则自动初始化默认配置。"""

    if not CONFIG_FILE.exists():
        return CliConfig()

    try:
        data = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
        return CliConfig.model_validate(data)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, ValidationError):
        # 配置损坏时先保留现场，避免后续 login/logout 覆盖掉其它 Profile。
        backup_path = CONFIG_FILE.with_name(f"{CONFIG_FILE.name}.corrupt.{time.time_ns()}")
        try:
            CONFIG_FILE.replace(backup_path)
        except OSError:
            pass
        return CliConfig()


def save_config(config: CliConfig) -> None:
    """持久化保存本地配置文件（在 POSIX 系统上设置 0600 权限防止凭据泄露）。"""

    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    content = json.dumps(config.model_dump(mode="json"), indent=2, ensure_ascii=False)
    temp_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=CONFIG_DIR,
            prefix=".config.",
            suffix=".tmp",
            delete=False,
        ) as temp_file:
            temp_path = Path(temp_file.name)
            temp_file.write(content)
            temp_file.flush()
            if os.name != "nt":
                temp_path.chmod(0o600)
        os.replace(temp_path, CONFIG_FILE)
        temp_path = None
    finally:
        if temp_path is not None:
            try:
                temp_path.unlink()
            except OSError:
                pass


def get_profile(config: CliConfig, profile_name: str | None = None) -> ProfileConfig:
    """获取指定或当前的 Profile 配置。"""

    name = profile_name or config.current_profile or DEFAULT_PROFILE
    if name not in config.profiles:
        config.profiles[name] = ProfileConfig()
    return config.profiles[name]
