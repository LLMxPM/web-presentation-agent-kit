"""文件功能：提供 External API Guides 索引与 operation 详情查询命令。"""

from __future__ import annotations

import click

from wp.client import ApiClient, ApiClientError
from wp.config import get_profile, load_config
from wp.formatter import print_error, print_json


@click.command("guide")
@click.argument("operation_key", required=False)
@click.pass_context
def guide_cmd(ctx: click.Context, operation_key: str | None) -> None:
    """读取全部操作索引，或读取一个 operation 的精确 JSON Schema。"""

    profile = get_profile(load_config(), ctx.obj.get("profile"))
    client = ApiClient(profile, workspace_id=ctx.obj.get("workspace_id"))
    try:
        print_json(client.get_operation_guide(operation_key))
    except ApiClientError as err:
        print_error(f"读取操作指南失败: {err.message}", code=err.code, details=err.details)
        raise SystemExit(1)
