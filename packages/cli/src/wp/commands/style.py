"""文件功能：处理样式方案管理（列表、详情、创建、复制、归档）。"""

from __future__ import annotations

import click

from wp.client import ApiClient, ApiClientError
from wp.config import get_profile, load_config
from wp.formatter import print_error, print_json, print_table
from wp.commands.common import (
    confirm_archive,
    get_client,
    handle_api_error,
    idempotency_key_option,
    output_result,
    read_json_file,
    require_ids,
    require_object,
)
from wp.openapi_help import contract, openapi_command


@click.group("style")
def style_group() -> None:
    """工作空间样式方案管理。"""


@openapi_command(style_group, "list", contract("GET", "/api/v1/styles"))
@click.option("--page", default=1, type=int, help="页码")
@click.option("--page-size", default=50, type=int, help="每页数量")
@click.pass_context
def list_styles_cmd(ctx: click.Context, page: int, page_size: int) -> None:
    """查询工作空间的样式方案列表。"""

    cfg = load_config()
    profile = get_profile(cfg, ctx.obj.get("profile"))
    client = ApiClient(profile, workspace_id=ctx.obj.get("workspace_id"))

    try:
        res = client.get("/styles", params={"page": page, "page_size": page_size})
        if ctx.obj.get("as_json"):
            print_json(res)
            return

        items = res.get("items", [])
        rows = [[s["id"], s.get("name", "-"), s.get("is_default", False), s.get("status", "-")] for s in items]
        print_table("样式方案列表", ["ID", "名称", "是否默认", "状态"], rows)
    except ApiClientError as err:
        print_error(f"获取样式列表失败: {err.message}", code=err.code)
        raise SystemExit(1)


@openapi_command(style_group, "get", contract("GET", "/api/v1/styles/{style_id}"))
@click.argument("style_id", type=int)
@click.pass_context
def get_style_cmd(ctx: click.Context, style_id: int) -> None:
    """获取单个样式方案详情。"""

    cfg = load_config()
    profile = get_profile(cfg, ctx.obj.get("profile"))
    client = ApiClient(profile, workspace_id=ctx.obj.get("workspace_id"))

    try:
        style = client.get(f"/styles/{style_id}")
        if ctx.obj.get("as_json"):
            print_json(style)
            return

        rows = [
            ["ID", str(style.get("id"))],
            ["名称", str(style.get("name"))],
            ["是否默认", str(style.get("is_default"))],
            ["描述", str(style.get("description") or "-")],
            ["状态", str(style.get("status"))],
        ]
        print_table(f"样式方案 (ID: {style_id}) 详情", ["属性", "值"], rows)
    except ApiClientError as err:
        print_error(f"获取样式方案失败: {err.message}", code=err.code)
        raise SystemExit(1)


@openapi_command(
    style_group,
    "create",
    contract("POST", "/api/v1/styles"),
    examples=("wp style create --payload-file ./style.json --idempotency-key style-corporate",),
)
@click.option("--name", "-n", help="样式方案名称")
@click.option("--description", "-d", help="样式描述")
@click.option(
    "--payload-file",
    type=click.Path(exists=True, dir_okay=False),
    help="完整样式创建 JSON；提供后忽略其它参数，支持 configuration.presentation 嵌套或顶层 page_width 等展示字段",
)
@idempotency_key_option
@click.pass_context
def create_style_cmd(ctx: click.Context, name: str | None, description: str | None, payload_file: str | None) -> None:
    """创建新样式方案；直接参数模式必须提供名称。"""

    try:
        if payload_file:
            payload = require_object(read_json_file(payload_file, label="样式创建载荷"), label="样式创建载荷")
        else:
            if not name:
                raise click.UsageError("未使用 --payload-file 时必须提供 --name。")
            payload = {"name": name, "description": description}
        output_result(ctx, get_client(ctx).post("/styles", json_data=payload))
    except ApiClientError as err:
        handle_api_error("创建样式方案失败", err)


@openapi_command(style_group, "update", contract("PATCH", "/api/v1/styles/{style_id}"))
@click.argument("style_id", type=int)
@click.option("--payload-file", type=click.Path(exists=True, dir_okay=False), required=True, help="样式元数据或 configuration 更新 JSON 请求体")
@idempotency_key_option
@click.pass_context
def update_style_cmd(ctx: click.Context, style_id: int, payload_file: str) -> None:
    """更新样式元数据和 configuration。"""

    try:
        output_result(ctx, get_client(ctx).patch(f"/styles/{style_id}", json_data=require_object(read_json_file(payload_file, label="样式更新载荷"), label="样式更新载荷")))
    except ApiClientError as err:
        handle_api_error("更新样式失败", err)


@openapi_command(style_group, "copy", contract("POST", "/api/v1/styles/{style_id}/copy"))
@click.argument("style_id", type=int)
@click.option("--payload-file", type=click.Path(exists=True, dir_okay=False), required=True, help="样式副本名称和说明 JSON 请求体")
@idempotency_key_option
@click.pass_context
def copy_style_cmd(ctx: click.Context, style_id: int, payload_file: str) -> None:
    """复制样式方案。"""

    try:
        output_result(ctx, get_client(ctx).post(f"/styles/{style_id}/copy", json_data=require_object(read_json_file(payload_file, label="样式复制载荷"), label="样式复制载荷")))
    except ApiClientError as err:
        handle_api_error("复制样式失败", err)


@openapi_command(
    style_group,
    "archive",
    contract("POST", "/api/v1/styles/{style_id}/archive", "提供 STYLE_ID 时"),
    contract("POST", "/api/v1/styles/batch-archive", "提供 --ids-file 时"),
)
@click.argument("style_id", type=int, required=False)
@click.option("--ids-file", type=click.Path(exists=True, dir_okay=False), help="批量归档的正整数 ID JSON 数组")
@click.option("--yes", "-y", is_flag=True, help="仅在用户已明确授权归档时跳过交互确认")
@idempotency_key_option
@click.pass_context
def archive_style_cmd(ctx: click.Context, style_id: int | None, ids_file: str | None, yes: bool) -> None:
    """归档样式方案（默认样式受保护禁止归档）。"""

    try:
        client = get_client(ctx)
        if ids_file:
            ids = require_ids(read_json_file(ids_file, label="归档 ID"))
            confirm_archive(ids, yes=yes, label="样式")
            output_result(ctx, client.post("/styles/batch-archive", json_data={"ids": ids}))
            return
        if style_id is None:
            raise click.UsageError("必须提供 style_id 或 --ids-file。")
        confirm_archive([style_id], yes=yes, label="样式")
        output_result(ctx, client.post(f"/styles/{style_id}/archive"))
    except ApiClientError as err:
        handle_api_error("归档样式方案失败", err)
