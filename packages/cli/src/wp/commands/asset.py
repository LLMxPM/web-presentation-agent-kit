"""文件功能：提供工作空间资源的查询、上传、文本内容、复制、更新与归档命令。"""

from __future__ import annotations

from pathlib import Path

import click

from wp.commands.common import (
    confirm_archive,
    get_client,
    handle_api_error,
    output_result,
    read_json_file,
    read_text_file,
    require_array,
    require_ids,
    require_object,
)
from wp.formatter import print_table


ASSET_TYPES = ["image", "icon", "font", "video", "drawio", "mermaid", "chart", "formula"]


@click.group("asset")
def asset_group() -> None:
    """工作空间静态资源管理。"""


@asset_group.command("list")
@click.option("--page", default=1, type=int)
@click.option("--page-size", default=50, type=int)
@click.option("--type", "asset_type", type=click.Choice(ASSET_TYPES))
@click.option("--keyword")
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
    except Exception as err:
        if hasattr(err, "message"):
            handle_api_error("获取资源列表失败", err)  # type: ignore[arg-type]
        raise


@asset_group.command("get")
@click.argument("asset_id", type=int)
@click.pass_context
def get_asset_cmd(ctx: click.Context, asset_id: int) -> None:
    """获取资源详情。"""

    try:
        output_result(ctx, get_client(ctx).get(f"/assets/{asset_id}"))
    except Exception as err:
        if hasattr(err, "message"):
            handle_api_error("获取资源详情失败", err)  # type: ignore[arg-type]
        raise


@asset_group.command("upload")
@click.argument("file_path", type=click.Path(exists=True, dir_okay=False))
@click.option("--type", "asset_type", type=click.Choice(ASSET_TYPES), required=True)
@click.option("--name")
@click.option("--description")
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
    except Exception as err:
        if hasattr(err, "message"):
            handle_api_error("上传资源失败", err)  # type: ignore[arg-type]
        raise


@asset_group.command("create")
@click.option("--payload-file", type=click.Path(exists=True, dir_okay=False), required=True)
@click.option("--content-file", type=click.Path(exists=True, dir_okay=False), help="覆盖 JSON 中 content 的文本文件")
@click.pass_context
def create_asset_cmd(ctx: click.Context, payload_file: str, content_file: str | None) -> None:
    """创建文本内容资源。"""

    payload = require_object(read_json_file(payload_file, label="资源创建载荷"), label="资源创建载荷")
    if content_file:
        payload["content"] = read_text_file(content_file, label="资源内容")
    try:
        output_result(ctx, get_client(ctx).post("/assets/content", json_data=payload))
    except Exception as err:
        if hasattr(err, "message"):
            handle_api_error("创建文本资源失败", err)  # type: ignore[arg-type]
        raise


@asset_group.group("content")
def asset_content_group() -> None:
    """可编辑文本资源内容。"""


@asset_content_group.command("get")
@click.argument("asset_id", type=int)
@click.pass_context
def get_asset_content_cmd(ctx: click.Context, asset_id: int) -> None:
    """读取资源文本内容。"""

    try:
        output_result(ctx, get_client(ctx).get(f"/assets/{asset_id}/content"))
    except Exception as err:
        if hasattr(err, "message"):
            handle_api_error("读取资源内容失败", err)  # type: ignore[arg-type]
        raise


@asset_content_group.command("update")
@click.argument("asset_id", type=int)
@click.option("--content-file", type=click.Path(exists=True, dir_okay=False), required=True)
@click.option("--change-note")
@click.pass_context
def update_asset_content_cmd(ctx: click.Context, asset_id: int, content_file: str, change_note: str | None) -> None:
    """写入资源文本内容。"""

    try:
        output_result(ctx, get_client(ctx).put(f"/assets/{asset_id}/content", json_data={"content": read_text_file(content_file, label="资源内容"), "change_note": change_note}))
    except Exception as err:
        if hasattr(err, "message"):
            handle_api_error("更新资源内容失败", err)  # type: ignore[arg-type]
        raise


@asset_content_group.command("preview")
@click.argument("asset_id", type=int)
@click.option("--content-file", type=click.Path(exists=True, dir_okay=False), required=True)
@click.pass_context
def preview_asset_content_cmd(ctx: click.Context, asset_id: int, content_file: str) -> None:
    """预览资源文本内容差异。"""

    try:
        output_result(ctx, get_client(ctx).post(f"/assets/{asset_id}/content/preview", json_data={"content": read_text_file(content_file, label="资源内容")}, idempotent=False))
    except Exception as err:
        if hasattr(err, "message"):
            handle_api_error("预览资源内容失败", err)  # type: ignore[arg-type]
        raise


@asset_group.group("tags")
def asset_tags_group() -> None:
    """资源标签。"""


@asset_tags_group.command("list")
@click.option("--type", "asset_type", type=click.Choice(ASSET_TYPES))
@click.pass_context
def list_asset_tags_cmd(ctx: click.Context, asset_type: str | None) -> None:
    """列出工作空间资源标签。"""

    try:
        params = {"asset_type": asset_type} if asset_type else None
        output_result(ctx, get_client(ctx).get("/assets/tags", params=params))
    except Exception as err:
        if hasattr(err, "message"):
            handle_api_error("获取资源标签失败", err)  # type: ignore[arg-type]
        raise


@asset_group.command("update")
@click.argument("asset_id", type=int)
@click.option("--payload-file", type=click.Path(exists=True, dir_okay=False), required=True)
@click.pass_context
def update_asset_cmd(ctx: click.Context, asset_id: int, payload_file: str) -> None:
    """更新资源元数据。"""

    try:
        output_result(ctx, get_client(ctx).patch(f"/assets/{asset_id}", json_data=require_object(read_json_file(payload_file, label="资源更新载荷"), label="资源更新载荷")))
    except Exception as err:
        if hasattr(err, "message"):
            handle_api_error("更新资源失败", err)  # type: ignore[arg-type]
        raise


@asset_group.command("copy")
@click.argument("asset_id", type=int)
@click.option("--payload-file", type=click.Path(exists=True, dir_okay=False), required=True)
@click.pass_context
def copy_asset_cmd(ctx: click.Context, asset_id: int, payload_file: str) -> None:
    """复制资源。"""

    try:
        output_result(ctx, get_client(ctx).post(f"/assets/{asset_id}/copy", json_data=require_object(read_json_file(payload_file, label="资源复制载荷"), label="资源复制载荷")))
    except Exception as err:
        if hasattr(err, "message"):
            handle_api_error("复制资源失败", err)  # type: ignore[arg-type]
        raise


@asset_group.command("archive")
@click.argument("asset_id", type=int, required=False)
@click.option("--ids-file", type=click.Path(exists=True, dir_okay=False))
@click.option("--yes", is_flag=True)
@click.pass_context
def archive_asset_cmd(ctx: click.Context, asset_id: int | None, ids_file: str | None, yes: bool) -> None:
    """归档单个或一批资源。"""

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
    except Exception as err:
        if hasattr(err, "message"):
            handle_api_error("归档资源失败", err)  # type: ignore[arg-type]
        raise
