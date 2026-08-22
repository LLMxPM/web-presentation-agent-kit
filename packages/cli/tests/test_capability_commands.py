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
    for command in ("system", "standards", "guide", "runtime-kit", "font", "job"):
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
