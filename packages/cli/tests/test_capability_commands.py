"""文件功能：验证首版 CLI 新增资源命令、文件载荷和复杂参数入口。"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).parents[1] / "src"))

from click.testing import CliRunner

from wp.cli import main


def test_new_command_groups_are_registered() -> None:
    """顶层和资源级能力分组应全部出现在帮助中。"""

    result = CliRunner().invoke(main, ["--help"])
    assert result.exit_code == 0
    for command in ("system", "standards", "runtime-kit", "font", "job"):
        assert command in result.output

    for args in (
        ["project", "configuration", "--help"],
        ["project", "route", "--help"],
        ["page", "version", "--help"],
        ["component", "version", "--help"],
        ["asset", "content", "--help"],
        ["asset", "tags", "--help"],
    ):
        nested = CliRunner().invoke(main, args)
        assert nested.exit_code == 0, (args, nested.output)


def test_project_update_reads_json_payload(tmp_path: Path) -> None:
    """项目更新应把 JSON 文件原样传给 External API。"""

    payload_file = tmp_path / "project.json"
    payload = {"name": "新项目", "description": "首版测试"}
    payload_file.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")

    fake_client = MagicMock()
    fake_client.patch.return_value = {"id": 7, "name": "新项目"}
    with patch("wp.commands.project.get_client", return_value=fake_client):
        result = CliRunner().invoke(main, ["--json", "project", "update", "7", "--payload-file", str(payload_file)])

    assert result.exit_code == 0, result.output
    fake_client.patch.assert_called_once_with("/projects/7", json_data=payload)
    assert '"id": 7' in result.output


def test_style_create_reads_flat_full_payload(tmp_path: Path) -> None:
    """样式创建应把包含完整顶层展示字段的 JSON 载荷传给 External API。"""

    payload_file = tmp_path / "style.json"
    payload = {
        "key": "flat-style",
        "name": "完整样式",
        "description": "CLI 测试",
        "page_width": 1920,
        "page_height": 1080,
        "base_font_size": "18px",
        "icon_default_stroke_width": 3,
        "show_pdf_export_button": False,
        "menu_mode": "bottom-preview",
        "theme_key": None,
        "style_spec_markdown": "## 规范",
    }
    payload_file.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")

    fake_client = MagicMock()
    fake_client.post.return_value = {"id": 13, "key": "flat-style"}
    with patch("wp.commands.style.get_client", return_value=fake_client):
        result = CliRunner().invoke(
            main,
            ["--json", "style", "create", "--payload-file", str(payload_file)],
        )

    assert result.exit_code == 0, result.output
    fake_client.post.assert_called_once_with("/styles", json_data=payload)


def test_style_create_help_describes_full_payload_fields() -> None:
    """样式创建帮助应说明完整 payload 支持的字段形态。"""

    result = CliRunner().invoke(main, ["style", "create", "--help"])

    assert result.exit_code == 0, result.output
    assert "configuration.presentation" in result.output
    assert "page_width" in result.output


def test_asset_content_update_reads_raw_text(tmp_path: Path) -> None:
    """资源内容更新应保持 UTF-8 文本原样，不把内容当 JSON 解析。"""

    content_file = tmp_path / "diagram.mmd"
    content = "graph TD\n  A-->B\n"
    content_file.write_text(content, encoding="utf-8")
    fake_client = MagicMock()
    fake_client.put.return_value = {"id": 3}
    with patch("wp.commands.asset.get_client", return_value=fake_client):
        result = CliRunner().invoke(main, ["--json", "asset", "content", "update", "3", "--content-file", str(content_file)])

    assert result.exit_code == 0, result.output
    fake_client.put.assert_called_once_with(
        "/assets/3/content",
        json_data={"content": content, "change_note": None},
    )


def test_archive_ids_file_rejects_non_integer_ids(tmp_path: Path) -> None:
    """批量归档文件必须是正整数数组。"""

    ids_file = tmp_path / "ids.json"
    ids_file.write_text(json.dumps([1, "two"]), encoding="utf-8")
    result = CliRunner().invoke(main, ["project", "archive", "--ids-file", str(ids_file), "--yes"])

    assert result.exit_code != 0
    assert "正整数" in result.output
