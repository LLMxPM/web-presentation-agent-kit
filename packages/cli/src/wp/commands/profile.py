"""文件功能：处理 CLI Profile 列表查看与默认 Profile 切换。"""

from __future__ import annotations

import click

from wp.config import get_profile, load_config, save_config
from wp.formatter import print_error, print_json, print_success, print_table


@click.group("profile")
def profile_group() -> None:
    """管理 Backend 地址、PAT 和默认工作空间所在的 Profile。"""


@profile_group.command("list")
@click.pass_context
def list_profiles_cmd(ctx: click.Context) -> None:
    """列出本地 Profile，不显示 PAT。"""

    cfg = load_config()
    profiles = {
        name: {
            "endpoint": profile.endpoint,
            "default_workspace_id": profile.default_workspace_id,
            "has_token": bool(profile.token),
        }
        for name, profile in sorted(cfg.profiles.items())
    }

    if ctx.obj.get("as_json"):
        print_json({"current_profile": cfg.current_profile, "profiles": profiles})
        return

    rows = []
    for name, profile in sorted(cfg.profiles.items()):
        marker = "*" if name == cfg.current_profile else ""
        rows.append([
            f"{marker} {name}".strip(),
            profile.endpoint,
            profile.default_workspace_id or "-",
            "已配置" if profile.token else "未配置",
        ])
    print_table(
        "本地 Profile (* 当前默认)",
        ["名称", "Backend 地址", "默认工作空间", "PAT"],
        rows,
    )


@profile_group.command("use")
@click.argument("profile_name")
def use_profile_cmd(profile_name: str) -> None:
    """将指定 Profile 设为后续命令使用的默认 Profile。"""

    cfg = load_config()
    if profile_name not in cfg.profiles:
        print_error(
            f"Profile 不存在: {profile_name}。请先使用 `wp --profile {profile_name} login ...` 创建。",
            code="PROFILE_NOT_FOUND",
        )
        raise SystemExit(1)

    cfg.current_profile = profile_name
    profile = get_profile(cfg, profile_name)
    save_config(cfg)
    workspace = profile.default_workspace_id or "未设置"
    print_success(
        f"已切换默认 Profile: [bold]{profile_name}[/bold] "
        f"(Backend: {profile.endpoint}, 工作空间: {workspace})"
    )
