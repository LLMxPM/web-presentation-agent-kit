"""文件功能：提供工作空间组件的查询、创建、编辑、校验、发布与归档命令。"""

from __future__ import annotations

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
    require_success_job,
    resolve_wait_job,
)
from wp.config import get_profile, load_config
from wp.formatter import print_table


@click.group("component")
def component_group() -> None:
    """工作空间组件管理与 Mutation 任务。"""


@component_group.command("list")
@click.option("--page", default=1, type=int)
@click.option("--page-size", default=50, type=int)
@click.option("--keyword")
@click.option("--scope", type=click.Choice(["all", "suggested"]), default="all")
@click.option("--project-id", type=int)
@click.pass_context
def list_components_cmd(ctx: click.Context, page: int, page_size: int, keyword: str | None, scope: str, project_id: int | None) -> None:
    """查询工作空间组件或项目建议组件。"""

    if scope == "suggested" and project_id is None:
        raise click.UsageError("scope=suggested 时必须提供 --project-id。")
    params = {"page": page, "page_size": page_size, "keyword": keyword, "scope": scope, "project_id": project_id}
    try:
        result = get_client(ctx).get("/components", params={key: value for key, value in params.items() if value is not None})
        if ctx.obj.get("as_json"):
            output_result(ctx, result)
            return
        rows = [
            [item.get("id"), item.get("import_name", "-"), item.get("name", "-"), item.get("component_type", "-"), item.get("status", "-")]
            for item in result.get("items", [])
        ]
        print_table("组件列表", ["ID", "导入标识", "名称", "类型", "状态"], rows)
    except Exception as err:
        if hasattr(err, "message"):
            handle_api_error("获取组件列表失败", err)  # type: ignore[arg-type]
        raise


@component_group.command("get")
@click.argument("component_id", type=int)
@click.pass_context
def get_component_cmd(ctx: click.Context, component_id: int) -> None:
    """获取组件详情。"""

    try:
        output_result(ctx, get_client(ctx).get(f"/components/{component_id}"))
    except Exception as err:
        if hasattr(err, "message"):
            handle_api_error("获取组件失败", err)  # type: ignore[arg-type]
        raise


@component_group.command("create")
@click.option("--name")
@click.option("--import-name")
@click.option("--file", "file_path", type=click.Path(exists=True, dir_okay=False))
@click.option("--type", "component_type", default="content")
@click.option("--description")
@click.option("--preview-schema-file", type=click.Path(exists=True, dir_okay=False))
@click.option("--payload-file", type=click.Path(exists=True, dir_okay=False))
@click.option("--wait/--no-wait", default=True)
@click.option("--timeout", type=float, default=120.0, show_default=True)
@click.pass_context
def create_component_cmd(
    ctx: click.Context,
    name: str | None,
    import_name: str | None,
    file_path: str | None,
    component_type: str,
    description: str | None,
    preview_schema_file: str | None,
    payload_file: str | None,
    wait: bool,
    timeout: float,
) -> None:
    """提交组件创建 Mutation Job。"""

    profile = get_profile(load_config(), ctx.obj.get("profile"))
    workspace_id = ctx.obj.get("workspace_id") or profile.default_workspace_id
    if not workspace_id:
        raise click.UsageError("必须通过 --workspace 或 Profile 默认配置指定工作空间。")
    if payload_file:
        payload = require_object(read_json_file(payload_file, label="组件创建载荷"), label="组件创建载荷")
    else:
        if not name or not import_name or not file_path:
            raise click.UsageError("未使用 --payload-file 时必须提供 --name、--import-name 和 --file。")
        payload = {
            "workspace_id": workspace_id,
            "import_name": import_name,
            "name": name,
            "component_type": component_type,
            "source_code": read_text_file(file_path, label="组件源码"),
            "description": description,
        }
    if preview_schema_file:
        payload["preview_schema"] = read_json_file(preview_schema_file, label="Preview Schema")
    try:
        client = get_client(ctx)
        result = resolve_wait_job(client, client.create_component(payload), wait=wait, timeout=timeout)
        if wait:
            require_success_job(result)
        output_result(ctx, result)
    except Exception as err:
        if hasattr(err, "message"):
            handle_api_error("提交组件创建失败", err)  # type: ignore[arg-type]
        raise


@component_group.command("update")
@click.argument("component_id", type=int)
@click.option("--payload-file", type=click.Path(exists=True, dir_okay=False), required=True)
@click.option("--preview-schema-file", type=click.Path(exists=True, dir_okay=False), help="覆盖 payload 中的 Preview Schema JSON")
@click.option("--wait/--no-wait", default=True)
@click.option("--timeout", type=float, default=120.0, show_default=True)
@click.pass_context
def update_component_cmd(
    ctx: click.Context,
    component_id: int,
    payload_file: str,
    preview_schema_file: str | None,
    wait: bool,
    timeout: float,
) -> None:
    """更新组件元数据，复杂字段自动进入异步校验任务。"""

    payload = require_object(read_json_file(payload_file, label="组件更新载荷"), label="组件更新载荷")
    if preview_schema_file:
        payload["preview_schema"] = require_object(
            read_json_file(preview_schema_file, label="Preview Schema"),
            label="Preview Schema",
        )
    try:
        client = get_client(ctx)
        if any(field in payload for field in ("import_name", "component_type", "preview_schema")):
            job = client.update_component_metadata_async({"component_id": component_id, **payload})
            result = resolve_wait_job(client, job, wait=wait, timeout=timeout)
            if wait:
                require_success_job(result)
            output_result(ctx, result)
            return
        output_result(ctx, client.patch(f"/components/{component_id}", json_data=payload))
    except Exception as err:
        if hasattr(err, "message"):
            handle_api_error("更新组件失败", err)  # type: ignore[arg-type]
        raise


@component_group.command("edit")
@click.argument("component_id", type=int)
@click.option("--edits-file", type=click.Path(exists=True, dir_okay=False), required=True)
@click.option("--base-version-no", type=int, required=True)
@click.option("--base-draft-hash", required=True)
@click.option("--wait/--no-wait", default=True)
@click.option("--timeout", type=float, default=120.0, show_default=True)
@click.pass_context
def edit_component_cmd(ctx: click.Context, component_id: int, edits_file: str, base_version_no: int, base_draft_hash: str, wait: bool, timeout: float) -> None:
    """提交组件源码结构化编辑任务。"""

    edits = require_array(read_json_file(edits_file, label="组件编辑操作"), label="组件编辑操作")
    try:
        client = get_client(ctx)
        payload = {"component_id": component_id, "base_version_no": base_version_no, "base_draft_hash": base_draft_hash, "edits": edits}
        result = resolve_wait_job(client, client.edit_component(component_id, payload), wait=wait, timeout=timeout)
        if wait:
            require_success_job(result)
        output_result(ctx, result)
    except Exception as err:
        if hasattr(err, "message"):
            handle_api_error("提交组件编辑失败", err)  # type: ignore[arg-type]
        raise


@component_group.group("version")
def component_version_group() -> None:
    """组件历史发布版本。"""


@component_version_group.command("list")
@click.argument("component_id", type=int)
@click.pass_context
def list_component_versions_cmd(ctx: click.Context, component_id: int) -> None:
    """列出组件版本。"""

    try:
        output_result(ctx, get_client(ctx).get(f"/components/{component_id}/versions"))
    except Exception as err:
        if hasattr(err, "message"):
            handle_api_error("获取组件版本失败", err)  # type: ignore[arg-type]
        raise


@component_version_group.command("get")
@click.argument("component_id", type=int)
@click.argument("version_no", type=int)
@click.pass_context
def get_component_version_cmd(ctx: click.Context, component_id: int, version_no: int) -> None:
    """获取组件指定版本。"""

    try:
        output_result(ctx, get_client(ctx).get(f"/components/{component_id}/versions/{version_no}"))
    except Exception as err:
        if hasattr(err, "message"):
            handle_api_error("获取组件版本内容失败", err)  # type: ignore[arg-type]
        raise


@component_group.command("dependencies")
@click.argument("component_id", type=int)
@click.pass_context
def component_dependencies_cmd(ctx: click.Context, component_id: int) -> None:
    """获取组件当前版本依赖。"""

    try:
        output_result(ctx, get_client(ctx).get(f"/components/{component_id}/dependencies"))
    except Exception as err:
        if hasattr(err, "message"):
            handle_api_error("获取组件依赖失败", err)  # type: ignore[arg-type]
        raise


@component_group.command("validate")
@click.argument("component_id", type=int)
@click.option("--mode", type=click.Choice(["current", "content", "edits"]), default="current")
@click.option("--source-file", type=click.Path(exists=True, dir_okay=False))
@click.option("--edits-file", type=click.Path(exists=True, dir_okay=False))
@click.option("--preview-schema-file", type=click.Path(exists=True, dir_okay=False))
@click.option("--detail", is_flag=True)
@click.pass_context
def validate_component_cmd(ctx: click.Context, component_id: int, mode: str, source_file: str | None, edits_file: str | None, preview_schema_file: str | None, detail: bool) -> None:
    """校验组件当前或候选源码。"""

    payload: dict[str, object] = {"entity_type": "component", "entity_id": component_id, "mode": mode, "detail": detail}
    if mode == "content":
        if not source_file:
            raise click.UsageError("content 模式必须提供 --source-file。")
        payload["source_code"] = read_text_file(source_file, label="组件源码")
    if mode == "edits":
        if not edits_file:
            raise click.UsageError("edits 模式必须提供 --edits-file。")
        payload["edits"] = require_array(read_json_file(edits_file, label="组件编辑操作"), label="组件编辑操作")
    if preview_schema_file:
        payload["preview_schema"] = require_object(read_json_file(preview_schema_file, label="Preview Schema"), label="Preview Schema")
    try:
        output_result(ctx, get_client(ctx).validate_entity(payload))
    except Exception as err:
        if hasattr(err, "message"):
            handle_api_error("组件校验失败", err)  # type: ignore[arg-type]
        raise


@component_group.command("publish")
@click.argument("component_id", type=int)
@click.option("--release-name")
@click.option("--change-note")
@click.pass_context
def publish_component_cmd(ctx: click.Context, component_id: int, release_name: str | None, change_note: str | None) -> None:
    """发布组件当前草稿。"""

    try:
        output_result(ctx, get_client(ctx).post(f"/components/{component_id}/publish", json_data={"release_name": release_name, "change_note": change_note}))
    except Exception as err:
        if hasattr(err, "message"):
            handle_api_error("发布组件失败", err)  # type: ignore[arg-type]
        raise


@component_group.command("archive")
@click.argument("component_id", type=int, required=False)
@click.option("--ids-file", type=click.Path(exists=True, dir_okay=False))
@click.option("--yes", is_flag=True)
@click.pass_context
def archive_component_cmd(ctx: click.Context, component_id: int | None, ids_file: str | None, yes: bool) -> None:
    """归档单个或一批组件。"""

    try:
        client = get_client(ctx)
        if ids_file:
            ids = require_ids(read_json_file(ids_file, label="归档 ID"))
            confirm_archive(ids, yes=yes, label="组件")
            output_result(ctx, client.post("/components/batch-archive", json_data={"ids": ids}))
            return
        if component_id is None:
            raise click.UsageError("必须提供 component_id 或 --ids-file。")
        confirm_archive([component_id], yes=yes, label="组件")
        output_result(ctx, client.post(f"/components/{component_id}/archive"))
    except Exception as err:
        if hasattr(err, "message"):
            handle_api_error("归档组件失败", err)  # type: ignore[arg-type]
        raise
