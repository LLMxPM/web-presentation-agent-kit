"""文件功能：定义 CLI 面向 Agent 的稳定 JSON 返回字段投影。"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from wp.output_fields import (
    ASSET_FIELDS,
    ASSET_LIST_FIELDS,
    COMPONENT_DETAIL_FIELDS,
    COMPONENT_LIST_FIELDS,
    PAGE_DETAIL_FIELDS,
    PAGE_LIST_FIELDS,
    PAGE_SOURCE_FIELDS,
    PAGINATION_FIELDS,
    PREVIEW_FIELDS,
    PROJECT_DETAIL_FIELDS,
    PROJECT_LIST_FIELDS,
    SUGGESTED_COMPONENT_FIELDS,
    STYLE_FIELDS,
    THEME_FIELDS,
    VALIDATION_FIELDS,
)


def _pick(value: Mapping[str, Any], fields: Sequence[str]) -> dict[str, Any]:
    """按字段白名单复制对象，保留服务端实际存在的可选字段。"""

    return {field: value[field] for field in fields if field in value}


def _project_collection(value: Any, item_fields: Sequence[str]) -> Any:
    """投影分页列表，同时保留统一分页元数据和 items。"""

    if not isinstance(value, Mapping):
        return value
    result = _pick(value, PAGINATION_FIELDS)
    items = value.get("items")
    if isinstance(items, list):
        result["items"] = [
            _pick(item, item_fields) if isinstance(item, Mapping) else item
            for item in items
        ]
    return result


def project_response(value: Any, profile: str, *, detail: bool = False) -> Any:
    """根据命令返回类型生成稳定的 Agent JSON；raw 模式由调用方提前绕过。"""

    if profile == "project_list":
        return _project_collection(value, PROJECT_LIST_FIELDS)
    if profile == "project_detail":
        return _pick(value, PROJECT_DETAIL_FIELDS) if isinstance(value, Mapping) else value
    if profile == "page_list":
        return _project_collection(value, PAGE_LIST_FIELDS)
    if profile == "page_detail":
        return _pick(value, PAGE_DETAIL_FIELDS) if isinstance(value, Mapping) else value
    if profile == "page_source":
        return _pick(value, PAGE_SOURCE_FIELDS) if isinstance(value, Mapping) else value
    if profile == "component_list":
        if isinstance(value, Mapping):
            items = value.get("items")
            if isinstance(items, list) and any(
                isinstance(item, Mapping) and "available" in item for item in items
            ):
                return _project_collection(value, SUGGESTED_COMPONENT_FIELDS)
        return _project_collection(value, COMPONENT_LIST_FIELDS)
    if profile == "component_detail":
        return _pick(value, COMPONENT_DETAIL_FIELDS) if isinstance(value, Mapping) else value
    if profile == "asset_list":
        return _project_collection(value, ASSET_LIST_FIELDS)
    if profile == "asset_detail":
        return _pick(value, ASSET_FIELDS) if isinstance(value, Mapping) else value
    if profile == "theme":
        if isinstance(value, Mapping) and isinstance(value.get("items"), list):
            return _project_collection(value, THEME_FIELDS)
        return _pick(value, THEME_FIELDS) if isinstance(value, Mapping) else value
    if profile == "style":
        if isinstance(value, Mapping) and isinstance(value.get("items"), list):
            return _project_collection(value, STYLE_FIELDS)
        return _pick(value, STYLE_FIELDS) if isinstance(value, Mapping) else value
    if profile == "validation":
        if not isinstance(value, Mapping):
            return value
        fields = VALIDATION_FIELDS + (("diagnostics",) if detail else ())
        return _pick(value, fields)
    if profile == "preview":
        return _pick(value, PREVIEW_FIELDS) if isinstance(value, Mapping) else value
    if profile == "archive":
        if not isinstance(value, Mapping) or not (
            "archived_ids" in value or "failed_ids" in value
        ):
            return value
        return _pick(value, ("archived_ids", "total"))
    raise ValueError(f"未知 CLI 输出投影: {profile}")


__all__ = ["project_response"]
