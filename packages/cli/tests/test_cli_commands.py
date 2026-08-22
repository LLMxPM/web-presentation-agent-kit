"""文件功能：测试 CLI 命令行工具 (wp) 的命令注册、参数解析、格式化输出与错误处理。"""

from __future__ import annotations

import sys
from pathlib import Path

# 确保能定位到 cli/src
sys.path.insert(0, str(Path(__file__).parents[1] / "src"))

from click.testing import CliRunner
from wp.cli import main
from wp.config import CliConfig, ProfileConfig, load_config, save_config
import wp.config as config_module


def test_cli_help() -> None:
    """测试 CLI 顶层与子命令帮助信息输出。"""

    runner = CliRunner()
    result = runner.invoke(main, ["--help"])
    assert result.exit_code == 0
    assert "Web Presentation 官方命令行工具 (wp)" in result.output
    assert "workspace" in result.output
    assert "project" in result.output
    assert "page" in result.output
    assert "component" in result.output
    assert "asset" in result.output
    assert "build" not in result.output
    assert "guide" not in result.output
    assert "job" in result.output
    assert "validate" in result.output
    assert "doctor" in result.output
    assert "screenshot" in result.output
    assert "profile" in result.output



def test_cli_doctor_unconfigured() -> None:
    """测试在未配置环境时的 doctor 输出。"""

    runner = CliRunner()
    result = runner.invoke(main, ["doctor"])
    assert result.exit_code == 0
    assert "CLI 诊断检查报告" in result.output
    assert "CLI 版本" in result.output


def test_cli_json_mode() -> None:
    """测试全局 --json 选项。"""

    runner = CliRunner()
    result = runner.invoke(main, ["--json", "doctor"])
    assert result.exit_code == 0
    assert "[" in result.output
    assert "CLI 版本" in result.output


def test_profile_list_json_does_not_expose_token(monkeypatch, tmp_path) -> None:
    """测试 Profile 列表包含默认空间但不输出 PAT。"""

    monkeypatch.setattr(config_module, "CONFIG_DIR", tmp_path)
    monkeypatch.setattr(config_module, "CONFIG_FILE", tmp_path / "config.json")
    save_config(
        CliConfig(
            current_profile="production",
            profiles={
                "default": ProfileConfig(token="default_secret"),
                "production": ProfileConfig(
                    endpoint="https://api.example.com",
                    token="production_secret",
                    default_workspace_id=42,
                ),
            },
        )
    )

    runner = CliRunner()
    result = runner.invoke(main, ["--json", "profile", "list"])

    assert result.exit_code == 0
    assert '"current_profile": "production"' in result.output
    assert '"default_workspace_id": 42' in result.output
    assert "production_secret" not in result.output


def test_profile_use_persists_current_profile(monkeypatch, tmp_path) -> None:
    """测试切换默认 Profile 会持久化当前 Profile。"""

    monkeypatch.setattr(config_module, "CONFIG_DIR", tmp_path)
    monkeypatch.setattr(config_module, "CONFIG_FILE", tmp_path / "config.json")
    save_config(
        CliConfig(
            profiles={
                "default": ProfileConfig(),
                "production": ProfileConfig(
                    endpoint="https://api.example.com",
                    default_workspace_id=42,
                ),
            }
        )
    )

    runner = CliRunner()
    result = runner.invoke(main, ["profile", "use", "production"])

    assert result.exit_code == 0
    assert load_config().current_profile == "production"
    assert "production" in result.output


def test_profile_use_rejects_unknown_profile(monkeypatch, tmp_path) -> None:
    """测试不能把不存在的 Profile 设置为默认 Profile。"""

    monkeypatch.setattr(config_module, "CONFIG_DIR", tmp_path)
    monkeypatch.setattr(config_module, "CONFIG_FILE", tmp_path / "config.json")
    save_config(CliConfig())

    runner = CliRunner()
    result = runner.invoke(main, ["profile", "use", "missing"])

    assert result.exit_code == 1
    assert "PROFILE_NOT_FOUND" in result.output
