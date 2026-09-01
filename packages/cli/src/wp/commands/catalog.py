"""文件功能：提供 Runtime Kit 能力目录和工作空间字体目录命令。"""

from __future__ import annotations

import click

from wp.client import ApiClientError
from wp.commands.common import get_client, handle_api_error, output_result
from wp.openapi_help import contract, openapi_command


@click.group("runtime-kit")
def runtime_kit_group() -> None:
    """Runtime Kit 公开能力目录。"""


@openapi_command(runtime_kit_group, "list", contract("GET", "/api/v1/runtime-kit"))
@click.option("--keyword", help="按名称、说明或导入路径搜索")
@click.option("--category", help="按服务端返回的能力分类筛选")
@click.option("--kind", help="按能力类型筛选，例如 component、composable、util 或 type")
@click.option("--base-name", help="按不含版本号的能力基础名称筛选")
@click.option("--version-no", type=int, help="筛选指定公开版本号")
@click.option("--include-all-versions", is_flag=True, help="返回所有公开版本；默认只返回推荐版本")
@click.pass_context
def runtime_kit_list_cmd(
    ctx: click.Context,
    keyword: str | None,
    category: str | None,
    kind: str | None,
    base_name: str | None,
    version_no: int | None,
    include_all_versions: bool,
) -> None:
    """查询 Runtime Kit 能力。"""

    params = {
        key: value
        for key, value in {
            "keyword": keyword,
            "category": category,
            "kind": kind,
            "base_name": base_name,
            "version_no": version_no,
            "include_all_versions": include_all_versions,
        }.items()
        if value is not None
    }
    try:
        output_result(ctx, get_client(ctx).list_runtime_kit(params=params))
    except ApiClientError as err:
        handle_api_error("获取 Runtime Kit 目录失败", err)


@openapi_command(runtime_kit_group, "get", contract("GET", "/api/v1/runtime-kit/{item}"))
@click.argument("item")
@click.pass_context
def runtime_kit_get_cmd(ctx: click.Context, item: str) -> None:
    """获取 Runtime Kit 单项能力详情。"""

    try:
        output_result(ctx, get_client(ctx).get_runtime_kit_item(item))
    except ApiClientError as err:
        handle_api_error("获取 Runtime Kit 能力失败", err)


@click.group("font")
def font_group() -> None:
    """工作空间注册字体目录。"""


@openapi_command(font_group, "list", contract("GET", "/api/v1/fonts"))
@click.option("--page", default=1, type=int, show_default=True, help="结果页码")
@click.option("--page-size", default=50, type=int, show_default=True, help="每页返回数量")
@click.option("--keyword", help="按字体名称或逻辑名搜索")
@click.pass_context
def font_list_cmd(ctx: click.Context, page: int, page_size: int, keyword: str | None) -> None:
    """查询工作空间注册字体。"""

    params = {"page": page, "page_size": page_size}
    if keyword:
        params["keyword"] = keyword
    try:
        output_result(ctx, get_client(ctx).list_fonts(params=params))
    except ApiClientError as err:
        handle_api_error("获取字体列表失败", err)
