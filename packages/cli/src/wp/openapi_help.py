"""文件功能：为 CLI 叶子命令追加当前 Backend OpenAPI 请求契约，失败时直接中止帮助输出。"""

from __future__ import annotations

from dataclasses import dataclass
import json
from typing import Any, Callable

import click

from wp.client import ApiClient, ApiClientError
from wp.config import get_profile, load_config
from wp.openapi_contracts import render_contract as _render_contract
from wp_api_client.openapi import safe_url


@dataclass(frozen=True)
class OpenApiContract:
    """描述一个 CLI 执行分支对应的实际 HTTP 方法、路径和触发条件。"""

    method: str
    path: str
    condition: str | None = None


class OpenApiHelpCommand(click.Command):
    """严格获取当前 Backend 契约后输出完整帮助。"""

    openapi_contracts: tuple[OpenApiContract, ...] = ()
    help_examples: tuple[str, ...] = ()

    def format_help(self, ctx: click.Context, formatter: click.HelpFormatter) -> None:
        """全部契约成功后才输出帮助；失败直接报告并非零退出。"""
        rendered_contracts = []
        if self.openapi_contracts:
            try:
                profile = get_profile(load_config(), ctx.find_root().params.get("profile"))
                client = ApiClient(profile)
                try:
                    schema = client.get_openapi_schema(timeout_seconds=2.0)
                    for item in self.openapi_contracts:
                        rendered_contracts.append((item, _render_contract(schema, item)))
                finally:
                    client.close()
            except (ApiClientError, OSError, ValueError) as exc:
                code = exc.code if isinstance(exc, ApiClientError) else "OPENAPI_INVALID"
                details = dict(exc.details or {}) if isinstance(exc, ApiClientError) else {"stage": "configuration"}
                metadata = getattr(client, "openapi_details", {}) if "client" in locals() else {}
                if isinstance(metadata, dict):
                    details = {**metadata, **details}
                details["command"] = ctx.command_path
                if "profile" in locals():
                    details.setdefault("url", safe_url(profile.endpoint.rstrip("/") + "/openapi.json"))
                message = exc.message if isinstance(exc, ApiClientError) else "无法加载契约配置。"
                if ctx.find_root().params.get("as_json"):
                    click.echo(json.dumps({"code": code, "message": message, "details": details}, ensure_ascii=False), err=True)
                else:
                    click.echo(f"[{code}] {message}\n" + json.dumps(details, ensure_ascii=False), err=True)
                ctx.exit(1)
        super().format_help(ctx, formatter)
        if self.help_examples:
            formatter.write_paragraph()
            formatter.write_heading("示例")
            for example in self.help_examples:
                formatter.write_text(example)
        if rendered_contracts:
            formatter.write_paragraph()
            formatter.write_heading("当前 Backend OpenAPI 请求契约")
        for item, rendered in rendered_contracts:
            label = f"{item.method.upper()} {item.path}"
            if item.condition:
                label += f"（{item.condition}）"
            formatter.write_paragraph()
            formatter.write_text(label)
            formatter.write(json.dumps(rendered, ensure_ascii=False, indent=2) + "\n")


def openapi_command(
    group: click.Group,
    name: str,
    *contracts: OpenApiContract,
    examples: tuple[str, ...] = (),
) -> Callable[[Callable[..., Any]], OpenApiHelpCommand]:
    """注册带 OpenAPI 帮助的叶子命令，契约只描述 CLI 实际调用的路由。"""

    def decorator(callback: Callable[..., Any]) -> OpenApiHelpCommand:
        command = group.command(name, cls=OpenApiHelpCommand)(callback)
        command.openapi_contracts = tuple(contracts)
        command.help_examples = examples
        return command

    return decorator


def contract(method: str, path: str, condition: str | None = None) -> OpenApiContract:
    """构造规范化 HTTP 契约描述。"""

    return OpenApiContract(method=method.upper(), path=path, condition=condition)
