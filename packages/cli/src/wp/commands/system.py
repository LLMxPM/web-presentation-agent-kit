"""文件功能：提供系统探活、开发标准和 External API 操作指南命令。"""

from __future__ import annotations

import click

from wp.commands.common import get_client, handle_api_error, output_result


@click.group("system")
def system_group() -> None:
    """系统信息与健康检查。"""


@system_group.command("version")
@click.pass_context
def system_version_cmd(ctx: click.Context) -> None:
    """获取 Backend 与 External API 版本。"""

    try:
        output_result(ctx, get_client(ctx).get("/system/version"))
    except Exception as err:
        if hasattr(err, "message"):
            handle_api_error("获取系统版本失败", err)  # type: ignore[arg-type]
        raise


@system_group.command("health")
@click.pass_context
def system_health_cmd(ctx: click.Context) -> None:
    """检查 Backend 数据库和 Redis 健康状态。"""

    try:
        output_result(ctx, get_client(ctx).get("/system/health"))
    except Exception as err:
        if hasattr(err, "message"):
            handle_api_error("检查系统健康失败", err)  # type: ignore[arg-type]
        raise


@click.group("standards")
def standards_group() -> None:
    """读取页面和组件开发标准。"""


def _standard(entity_type: str, ctx: click.Context) -> None:
    """读取指定资源的标准规范。"""

    try:
        output_result(ctx, get_client(ctx).get_standard(entity_type))
    except Exception as err:
        if hasattr(err, "message"):
            handle_api_error("读取开发标准失败", err)  # type: ignore[arg-type]
        raise


@standards_group.command("page")
@click.pass_context
def page_standards_cmd(ctx: click.Context) -> None:
    """读取页面开发标准。"""

    _standard("page", ctx)


@standards_group.command("component")
@click.pass_context
def component_standards_cmd(ctx: click.Context) -> None:
    """读取组件开发标准。"""

    _standard("component", ctx)


@click.group("guide")
def guide_group() -> None:
    """读取 External API 操作指南。"""


@guide_group.command("list")
@click.pass_context
def guide_list_cmd(ctx: click.Context) -> None:
    """列出当前 External API 操作。"""

    try:
        output_result(ctx, get_client(ctx).get_operation_guide())
    except Exception as err:
        if hasattr(err, "message"):
            handle_api_error("获取操作指南列表失败", err)  # type: ignore[arg-type]
        raise


@guide_group.command("get")
@click.argument("operation_key")
@click.pass_context
def guide_get_cmd(ctx: click.Context, operation_key: str) -> None:
    """获取单个 External API 操作的 HTTP 与 JSON Schema 契约。"""

    try:
        output_result(ctx, get_client(ctx).get_operation_guide(operation_key))
    except Exception as err:
        if hasattr(err, "message"):
            handle_api_error("获取操作指南详情失败", err)  # type: ignore[arg-type]
        raise
