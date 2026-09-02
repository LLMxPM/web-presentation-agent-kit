"""文件功能：解析 Agent Skill 的全局/项目目录，并合并共享的安装目标。"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import subprocess

SUPPORTED_AGENTS = ("codex", "cursor", "copilot", "gemini", "opencode", "claude", "qoder")
SHARED_AGENTS = frozenset({"codex", "cursor", "copilot", "gemini", "opencode"})


@dataclass(frozen=True)
class SkillTarget:
    """表示一个实际写入目录及共用该目录的 Agent 集合。"""

    path: Path
    base: Path
    agents: tuple[str, ...]
    scope: str


def resolve_project_root(project_dir: Path | None = None) -> Path:
    """解析项目根目录；显式目录优先，否则使用 Git 根并回退当前目录。"""

    if project_dir is not None:
        return project_dir.expanduser().resolve()
    current = Path.cwd().resolve()
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            cwd=current,
            check=True,
            capture_output=True,
            text=True,
            timeout=5,
        )
        return Path(result.stdout.strip()).resolve()
    except (FileNotFoundError, subprocess.SubprocessError):
        return current


def normalize_agents(agents: tuple[str, ...]) -> tuple[str, ...]:
    """展开 all 并拒绝混用或未知 Agent。"""

    if not agents:
        raise ValueError("至少需要选择一个 Agent。")
    if "all" in agents:
        if len(agents) != 1:
            raise ValueError("--agent all 不能与其它 Agent 同时使用。")
        return SUPPORTED_AGENTS
    unknown = sorted(set(agents) - set(SUPPORTED_AGENTS))
    if unknown:
        raise ValueError(f"不支持的 Agent: {', '.join(unknown)}")
    return tuple(dict.fromkeys(agents))


def plan_targets(
    skill_name: str,
    *,
    scope: str,
    agents: tuple[str, ...],
    project_dir: Path | None = None,
    home_dir: Path | None = None,
) -> list[SkillTarget]:
    """为所选 Agent 生成去重后的安装目标，并保留共享关系。"""

    selected = normalize_agents(agents)
    if scope not in {"global", "project"}:
        raise ValueError(f"不支持的安装范围: {scope}")
    base = (home_dir or Path.home()).expanduser().resolve() if scope == "global" else resolve_project_root(project_dir)
    groups: list[tuple[Path, tuple[str, ...]]] = []

    shared = tuple(agent for agent in selected if agent in SHARED_AGENTS)
    if shared:
        groups.append((base / ".agents" / "skills", shared))
    if "claude" in selected:
        groups.append((base / ".claude" / "skills", ("claude",)))
    if "qoder" in selected:
        groups.append((base / ".qoder" / "skills", ("qoder",)))

    return [
        SkillTarget(path=root / skill_name, base=base, agents=group_agents, scope=scope)
        for root, group_agents in groups
    ]

