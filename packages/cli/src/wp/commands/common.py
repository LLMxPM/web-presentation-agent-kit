"""文件功能：提供 CLI 命令共享的客户端、文件载荷、异步任务和输出辅助函数。"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, NoReturn

import click

from wp.client import ApiClient, ApiClientError
from wp.config import get_profile, load_config
from wp.formatter import print_error, print_json


def get_client(ctx: click.Context) -> ApiClient:
    """根据当前命令上下文创建绑定 Profile 和 Workspace 的 API Client。"""

    profile = get_profile(load_config(), ctx.obj.get("profile"))
    return ApiClient(profile, workspace_id=ctx.obj.get("workspace_id"))


def read_json_file(file_path: str, *, label: str = "JSON 文件") -> Any:
    """读取 UTF-8 JSON 文件，并把文件错误转换为 Click 参数错误。"""

    try:
        content = Path(file_path).read_text(encoding="utf-8")
        return json.loads(content)
    except (OSError, UnicodeDecodeError) as exc:
        raise click.ClickException(f"无法读取{label} '{file_path}': {exc}") from exc
    except json.JSONDecodeError as exc:
        raise click.ClickException(f"{label} '{file_path}' 不是合法 JSON: {exc}") from exc


def read_text_file(file_path: str, *, label: str = "文本文件") -> str:
    """读取 UTF-8 文本文件，保留原始内容。"""

    try:
        return Path(file_path).read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        raise click.ClickException(f"无法读取{label} '{file_path}': {exc}") from exc


def require_object(value: Any, *, label: str) -> dict[str, Any]:
    """校验载荷根节点必须为 JSON 对象。"""

    if not isinstance(value, dict):
        raise click.ClickException(f"{label}必须是 JSON 对象。")
    return value


def require_array(value: Any, *, label: str) -> list[Any]:
    """校验载荷根节点必须为 JSON 数组。"""

    if not isinstance(value, list):
        raise click.ClickException(f"{label}必须是 JSON 数组。")
    return value


def require_ids(value: Any, *, label: str = "ID 列表") -> list[int]:
    """校验批量归档文件是只包含正整数 ID 的 JSON 数组。"""

    items = require_array(value, label=label)
    if any(isinstance(item, bool) or not isinstance(item, int) or item < 1 for item in items):
        raise click.ClickException(f"{label}必须是只包含正整数的 JSON 数组。")
    return items


def output_result(ctx: click.Context, value: Any) -> None:
    """输出命令结果；复杂响应统一使用 JSON，保证 CLI 与 Agent 消费一致。"""

    print_json(value)


def handle_api_error(message: str, error: ApiClientError) -> NoReturn:
    """统一打印结构化 API 错误并以非零状态退出。"""

    print_error(f"{message}: {error.message}", code=error.code, details=error.details)
    raise SystemExit(1)


def resolve_wait_job(
    client: ApiClient,
    job: dict[str, Any],
    *,
    wait: bool,
    timeout: float,
) -> dict[str, Any]:
    """按命令的 wait 选择返回入队结果或任务终态。"""

    if not wait:
        return job
    job_id = str(job.get("job_id") or "")
    if not job_id:
        raise click.ClickException("服务端未返回 job_id，无法等待异步任务。")
    return client.poll_mutation_job(job_id, timeout_seconds=timeout)


def require_success_job(job: dict[str, Any]) -> dict[str, Any]:
    """将失败或取消的任务转换为 CLI 失败退出。"""

    if job.get("status") in {"failed", "canceled"}:
        error = job.get("error") or {}
        raise click.ClickException(str(error.get("message") or "异步任务执行失败。"))
    return job


def confirm_archive(ids: list[int], *, yes: bool, label: str) -> None:
    """对单项或批量归档执行统一确认。"""

    if yes:
        return
    if not click.confirm(f"确定要归档 {label} {', '.join(map(str, ids))} 吗？"):
        raise click.Abort()


__all__ = [
    "confirm_archive",
    "get_client",
    "handle_api_error",
    "output_result",
    "read_json_file",
    "read_text_file",
    "require_array",
    "require_ids",
    "require_object",
    "require_success_job",
    "resolve_wait_job",
]
