"""文件功能：提供系统探活与页面、组件开发标准命令。"""

from __future__ import annotations

import click

from wp.client import ApiClientError
from wp.commands.common import get_client, handle_api_error, output_result
from wp.openapi_help import contract, openapi_command


@click.group("system")
def system_group() -> None:
    """系统信息与健康检查。"""


@openapi_command(system_group, "version", contract("GET", "/api/v1/system/version"))
@click.pass_context
def system_version_cmd(ctx: click.Context) -> None:
    """获取 Backend 与 External API 版本。"""

    try:
        output_result(ctx, get_client(ctx).get("/system/version"))
    except ApiClientError as err:
        handle_api_error("获取系统版本失败", err)


@openapi_command(system_group, "health", contract("GET", "/api/v1/system/health"))
@click.pass_context
def system_health_cmd(ctx: click.Context) -> None:
    """检查 Backend 数据库和 Redis 健康状态。"""

    try:
        output_result(ctx, get_client(ctx).get("/system/health"))
    except ApiClientError as err:
        handle_api_error("检查系统健康失败", err)


@click.group("standards")
def standards_group() -> None:
    """读取页面和组件开发标准。"""


def _standard(entity_type: str, ctx: click.Context) -> None:
    """读取指定资源的标准规范。"""

    try:
        output_result(ctx, get_client(ctx).get_standard(entity_type))
    except ApiClientError as err:
        handle_api_error("读取开发标准失败", err)


@openapi_command(standards_group, "page", contract("GET", "/api/v1/standards/page"))
@click.pass_context
def page_standards_cmd(ctx: click.Context) -> None:
    """读取页面开发标准。"""

    _standard("page", ctx)


@openapi_command(standards_group, "component", contract("GET", "/api/v1/standards/component"))
@click.pass_context
def component_standards_cmd(ctx: click.Context) -> None:
    """读取组件开发标准。"""

    _standard("component", ctx)
