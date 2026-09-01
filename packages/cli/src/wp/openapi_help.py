"""文件功能：为 CLI 叶子命令追加当前 Backend OpenAPI 请求契约，保持离线帮助可用。"""

from __future__ import annotations

from dataclasses import dataclass
import json
from typing import Any, Callable, Iterable

import click

from wp.client import ApiClient, ApiClientError
from wp.config import get_profile, load_config


@dataclass(frozen=True)
class OpenApiContract:
    """描述一个 CLI 执行分支对应的实际 HTTP 方法、路径和触发条件。"""

    method: str
    path: str
    condition: str | None = None


class OpenApiHelpCommand(click.Command):
    """先输出本地 Click 帮助，再尽力附加服务端 OpenAPI 请求 Schema。"""

    openapi_contracts: tuple[OpenApiContract, ...] = ()
    help_examples: tuple[str, ...] = ()

    def format_help(self, ctx: click.Context, formatter: click.HelpFormatter) -> None:
        """渲染帮助；OpenAPI 失败只降级提示，不改变 help 成功语义。"""

        super().format_help(ctx, formatter)
        if self.help_examples:
            formatter.write_paragraph()
            formatter.write_heading("示例")
            for example in self.help_examples:
                formatter.write_text(example)
        if not self.openapi_contracts:
            return
        formatter.write_paragraph()
        formatter.write_heading("当前 Backend OpenAPI 请求契约")
        try:
            profile_name = ctx.find_root().params.get("profile")
            profile = get_profile(load_config(), profile_name)
            client = ApiClient(profile)
            try:
                schema = client.get_openapi_schema(timeout_seconds=2.0)
            finally:
                client.close()
        except (ApiClientError, OSError, ValueError):
            formatter.write_text("当前 Backend Schema 未加载；以上本地帮助仍然有效。")
            return

        for contract in self.openapi_contracts:
            rendered = _render_contract(schema, contract)
            if rendered is None:
                formatter.write_text(f"OpenAPI 未包含 {contract.method.upper()} {contract.path}。")
                continue
            label = f"{contract.method.upper()} {contract.path}"
            if contract.condition:
                label = f"{label}（{contract.condition}）"
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


def _render_contract(openapi: dict[str, Any], contract: OpenApiContract) -> dict[str, Any] | None:
    """提取参数、请求体及其递归引用的组件 Schema。"""

    path_item = openapi.get("paths", {}).get(contract.path)
    if not isinstance(path_item, dict):
        return None
    operation = path_item.get(contract.method.lower())
    if not isinstance(operation, dict):
        return None

    parameters = [
        *(_as_dict_list(path_item.get("parameters"))),
        *(_as_dict_list(operation.get("parameters"))),
    ]
    request_body = operation.get("requestBody")
    result: dict[str, Any] = {
        "parameters": parameters,
        "requestBody": request_body if isinstance(request_body, dict) else None,
    }
    referenced = _collect_referenced_schemas(
        [parameters, request_body],
        openapi.get("components", {}).get("schemas", {}),
    )
    if referenced:
        result["referencedSchemas"] = referenced
    return result


def _as_dict_list(value: Any) -> list[dict[str, Any]]:
    """只保留 OpenAPI 参数列表中的对象项。"""

    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]


def _collect_referenced_schemas(values: Iterable[Any], schemas: Any) -> dict[str, Any]:
    """递归收集本次请求使用的 `#/components/schemas/*`，并处理循环引用。"""

    if not isinstance(schemas, dict):
        return {}
    collected: dict[str, Any] = {}

    def visit(value: Any) -> None:
        if isinstance(value, dict):
            ref = value.get("$ref")
            if isinstance(ref, str) and ref.startswith("#/components/schemas/"):
                name = ref.rsplit("/", 1)[-1]
                target = schemas.get(name)
                if name not in collected and isinstance(target, dict):
                    collected[name] = target
                    visit(target)
            for item in value.values():
                visit(item)
        elif isinstance(value, list):
            for item in value:
                visit(item)

    for value in values:
        visit(value)
    return collected


__all__ = ["OpenApiContract", "OpenApiHelpCommand", "contract", "openapi_command"]
