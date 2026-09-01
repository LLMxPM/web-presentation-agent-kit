"""文件功能：提供工作空间资源的查询、上传、文本内容、复制、更新与归档命令。"""

from __future__ import annotations

from pathlib import Path

import click

from wp.client import ApiClientError
from wp.commands.common import (
    confirm_archive,
    get_client,
    handle_api_error,
    idempotency_key_option,
    output_result,
    read_json_file,
    read_text_file,
    require_ids,
    require_object,
)
from wp.formatter import print_table
from wp.openapi_help import contract, openapi_command


ASSET_TYPES = ["image", "icon", "font", "video", "drawio", "mermaid", "chart", "formula"]


@click.group("asset")
def asset_group() -> None:
    """工作空间静态资源管理。"""


@openapi_command(asset_group, "list", contract("GET", "/api/v1/assets"))
@click.option("--page", default=1, type=int, show_default=True, help="结果页码")
@click.option("--page-size", default=50, type=int, show_default=True, help="每页返回数量")
@click.option("--type", "asset_type", type=click.Choice(ASSET_TYPES), help="按资源业务类型筛选")
@click.option("--keyword", help="按资源名称、说明或标签搜索")
@click.pass_context
def list_assets_cmd(ctx: click.Context, page: int, page_size: int, asset_type: str | None, keyword: str | None) -> None:
    """查询工作空间资源。"""

    params = {"page": page, "page_size": page_size, "asset_type": asset_type, "keyword": keyword}
    try:
        result = get_client(ctx).get("/assets", params={key: value for key, value in params.items() if value is not None})
        if ctx.obj.get("as_json"):
            output_result(ctx, result)
            return
        rows = [[item.get("id"), item.get("name", "-"), item.get("asset_type", "-"), item.get("status", "-")] for item in result.get("items", [])]
        print_table("资源列表", ["ID", "名称", "类型", "状态"], rows)
    except ApiClientError as err:
        handle_api_error("获取资源列表失败", err)


@openapi_command(asset_group, "get", contract("GET", "/api/v1/assets/{asset_id}"))
@click.argument("asset_id", type=int)
@click.pass_context
def get_asset_cmd(ctx: click.Context, asset_id: int) -> None:
    """获取资源详情。"""

    try:
        output_result(ctx, get_client(ctx).get(f"/assets/{asset_id}"))
    except ApiClientError as err:
        handle_api_error("获取资源详情失败", err)


@openapi_command(
    asset_group,
    "upload",
    contract("POST", "/api/v1/assets"),
    examples=("wp asset upload ./hero.png --type image --name hero-image --idempotency-key asset-hero-image",),
)
@click.argument("file_path", type=click.Path(exists=True, dir_okay=False))
@click.option("--type", "asset_type", type=click.Choice(ASSET_TYPES), required=True, help="上传资源类型")
@click.option("--name", help="平台逻辑名；默认使用文件名主干")
@click.option("--description", help="资源内容、来源和使用场景说明")
@idempotency_key_option
@click.pass_context
def upload_asset_cmd(ctx: click.Context, file_path: str, asset_type: str, name: str | None, description: str | None) -> None:
    """上传二进制或图片资源。"""

    path = Path(file_path)
    try:
        with path.open("rb") as file_obj:
            result = get_client(ctx).upload(
                "/assets",
                files={"file": (path.name, file_obj)},
                data={"asset_type": asset_type, "name": name or path.stem, "description": description},
            )
        output_result(ctx, result)
    except ApiClientError as err:
        handle_api_error("上传资源失败", err)


@openapi_command(
    asset_group,
    "create",
    contract("POST", "/api/v1/assets/content"),
    examples=("wp asset create --payload-file ./asset.json --content-file ./diagram.mmd --idempotency-key asset-diagram",),
)
@click.option("--payload-file", type=click.Path(exists=True, dir_okay=False), required=True, help="文本资源创建 JSON 请求体")
@click.option("--content-file", type=click.Path(exists=True, dir_okay=False), help="覆盖 JSON 中 content 的文本文件")
@idempotency_key_option
@click.pass_context
def create_asset_cmd(ctx: click.Context, payload_file: str, content_file: str | None) -> None:
    """创建文本内容资源。"""

    payload = require_object(read_json_file(payload_file, label="资源创建载荷"), label="资源创建载荷")
    if content_file:
        payload["content"] = read_text_file(content_file, label="资源内容")
    try:
        output_result(ctx, get_client(ctx).post("/assets/content", json_data=payload))
    except ApiClientError as err:
        handle_api_error("创建文本资源失败", err)


@asset_group.group("content")
def asset_content_group() -> None:
    """可编辑文本资源内容。"""


@openapi_command(asset_content_group, "get", contract("GET", "/api/v1/assets/{asset_id}/content"))
@click.argument("asset_id", type=int)
@click.pass_context
def get_asset_content_cmd(ctx: click.Context, asset_id: int) -> None:
    """读取资源文本内容。"""

    try:
        output_result(ctx, get_client(ctx).get(f"/assets/{asset_id}/content"))
    except ApiClientError as err:
        handle_api_error("读取资源内容失败", err)


@openapi_command(asset_content_group, "update", contract("PUT", "/api/v1/assets/{asset_id}/content"))
@click.argument("asset_id", type=int)
@click.option("--content-file", type=click.Path(exists=True, dir_okay=False), required=True, help="要写入的完整 UTF-8 文本内容")
@click.option("--change-note", help="本次完整内容替换的变更说明")
@idempotency_key_option
@click.pass_context
def update_asset_content_cmd(ctx: click.Context, asset_id: int, content_file: str, change_note: str | None) -> None:
    """写入资源文本内容。"""

    try:
        output_result(ctx, get_client(ctx).put(f"/assets/{asset_id}/content", json_data={"content": read_text_file(content_file, label="资源内容"), "change_note": change_note}))
    except ApiClientError as err:
        handle_api_error("更新资源内容失败", err)


@openapi_command(asset_content_group, "preview", contract("POST", "/api/v1/assets/{asset_id}/content/preview"))
@click.argument("asset_id", type=int)
@click.option("--content-file", type=click.Path(exists=True, dir_okay=False), required=True, help="用于生成差异且不会写入的候选 UTF-8 文本")
@click.pass_context
def preview_asset_content_cmd(ctx: click.Context, asset_id: int, content_file: str) -> None:
    """预览资源文本内容差异。"""

    try:
        output_result(ctx, get_client(ctx).post(f"/assets/{asset_id}/content/preview", json_data={"content": read_text_file(content_file, label="资源内容")}, idempotent=False))
    except ApiClientError as err:
        handle_api_error("预览资源内容失败", err)


@asset_group.group("tags")
def asset_tags_group() -> None:
    """资源标签。"""


@openapi_command(asset_tags_group, "list", contract("GET", "/api/v1/assets/tags"))
@click.option("--type", "asset_type", type=click.Choice(ASSET_TYPES), help="只返回指定资源类型使用的标签")
@click.pass_context
def list_asset_tags_cmd(ctx: click.Context, asset_type: str | None) -> None:
    """列出工作空间资源标签。"""

    try:
        params = {"asset_type": asset_type} if asset_type else None
        output_result(ctx, get_client(ctx).get("/assets/tags", params=params))
    except ApiClientError as err:
        handle_api_error("获取资源标签失败", err)


@openapi_command(asset_group, "update", contract("PATCH", "/api/v1/assets/{asset_id}"))
@click.argument("asset_id", type=int)
@click.option("--payload-file", type=click.Path(exists=True, dir_okay=False), required=True, help="资源元数据更新 JSON 请求体")
@idempotency_key_option
@click.pass_context
def update_asset_cmd(ctx: click.Context, asset_id: int, payload_file: str) -> None:
    """更新资源元数据。"""

    try:
        output_result(ctx, get_client(ctx).patch(f"/assets/{asset_id}", json_data=require_object(read_json_file(payload_file, label="资源更新载荷"), label="资源更新载荷")))
    except ApiClientError as err:
        handle_api_error("更新资源失败", err)


@openapi_command(asset_group, "copy", contract("POST", "/api/v1/assets/{asset_id}/copy"))
@click.argument("asset_id", type=int)
@click.option("--payload-file", type=click.Path(exists=True, dir_okay=False), required=True, help="资源副本名称、说明等 JSON 请求体")
@idempotency_key_option
@click.pass_context
def copy_asset_cmd(ctx: click.Context, asset_id: int, payload_file: str) -> None:
    """复制资源。"""

    try:
        output_result(ctx, get_client(ctx).post(f"/assets/{asset_id}/copy", json_data=require_object(read_json_file(payload_file, label="资源复制载荷"), label="资源复制载荷")))
    except ApiClientError as err:
        handle_api_error("复制资源失败", err)


@openapi_command(
    asset_group,
    "archive",
    contract("POST", "/api/v1/assets/{asset_id}/archive", "提供 ASSET_ID 时"),
    contract("POST", "/api/v1/assets/batch-archive", "提供 --ids-file 时"),
)
@click.argument("asset_id", type=int, required=False)
@click.option("--ids-file", type=click.Path(exists=True, dir_okay=False), help="批量归档的正整数 ID JSON 数组")
@click.option("--yes", is_flag=True, help="仅在用户已明确授权归档时跳过交互确认")
@idempotency_key_option
@click.pass_context
def archive_asset_cmd(ctx: click.Context, asset_id: int | None, ids_file: str | None, yes: bool) -> None:
    """归档单个资源或 JSON 数组指定的一批资源；两种目标输入只能选一种。"""

    try:
        client = get_client(ctx)
        if ids_file:
            ids = require_ids(read_json_file(ids_file, label="归档 ID"))
            confirm_archive(ids, yes=yes, label="资源")
            output_result(ctx, client.post("/assets/batch-archive", json_data={"ids": ids}))
            return
        if asset_id is None:
            raise click.UsageError("必须提供 asset_id 或 --ids-file。")
        confirm_archive([asset_id], yes=yes, label="资源")
        output_result(ctx, client.post(f"/assets/{asset_id}/archive"))
    except ApiClientError as err:
        handle_api_error("归档资源失败", err)
