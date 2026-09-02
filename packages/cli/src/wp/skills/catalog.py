"""文件功能：读取内置 Skill 清单、校验版本兼容性并计算规范化内容哈希。"""

from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
import hashlib
from importlib import resources
import json
from pathlib import Path
import re
import tomllib
from typing import Iterator

from wp import __version__

INSTALL_MARKER = ".wp-install.json"
_SEMVER_PATTERN = re.compile(r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)$")
_SKILL_NAME_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


@dataclass(frozen=True)
class BundledSkill:
    """描述随 CLI 发布的 Skill 版本、兼容范围、内容位置与摘要。"""

    name: str
    version: str
    requires_cli: str
    content_sha256: str
    root: Path


def parse_semver(value: str) -> tuple[int, int, int]:
    """解析本功能使用的严格三段式 SemVer，不接受隐式补位。"""

    match = _SEMVER_PATTERN.fullmatch(value)
    if not match:
        raise ValueError(f"无效的 SemVer: {value}")
    return tuple(int(part) for part in match.groups())  # type: ignore[return-value]


def version_satisfies(version: str, requirement: str) -> bool:
    """判断 CLI 版本是否满足由逗号分隔的 >=、>、<=、<、== 约束。"""

    current = parse_semver(version)
    for raw_clause in requirement.split(","):
        clause = raw_clause.strip()
        operator = next((item for item in (">=", "<=", "==", ">", "<") if clause.startswith(item)), None)
        if operator is None:
            raise ValueError(f"不支持的版本约束: {clause}")
        expected = parse_semver(clause[len(operator) :].strip())
        matched = {
            ">=": current >= expected,
            "<=": current <= expected,
            "==": current == expected,
            ">": current > expected,
            "<": current < expected,
        }[operator]
        if not matched:
            return False
    return True


def hash_skill_directory(root: Path) -> str:
    """按相对 POSIX 路径和文件内容计算稳定 SHA-256，忽略安装标记。"""

    digest = hashlib.sha256()
    files = sorted(
        (
            (path.relative_to(root).as_posix(), path)
            for path in root.rglob("*")
            if path.is_file() and path.name != INSTALL_MARKER
        ),
        key=lambda item: item[0],
    )
    for relative_path, path in files:
        digest.update(relative_path.encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return f"sha256:{digest.hexdigest()}"


def _development_skills_root() -> Path:
    """返回源码运行时的顶层 skills 目录，供未经过构建钩子的测试使用。"""

    return Path(__file__).resolve().parents[5] / "skills"


@contextmanager
def _materialized_resources() -> Iterator[tuple[Path, Path]]:
    """将包内 Skill 资源暴露为真实路径；源码模式回退到仓库顶层目录。"""

    packaged_root = resources.files("wp").joinpath("_bundled_skills")
    manifest_resource = packaged_root.joinpath("manifest.json")
    if manifest_resource.is_file():
        with resources.as_file(packaged_root) as resource_path:
            yield Path(resource_path), Path(resource_path) / "manifest.json"
        return

    source_root = _development_skills_root()
    yield source_root, source_root / "catalog.toml"


def _validate_skill(name: str, version: str, requires_cli: str, root: Path) -> None:
    """校验内置 Skill 的名称、版本、入口文件和 CLI 兼容声明。"""

    if not _SKILL_NAME_PATTERN.fullmatch(name):
        raise RuntimeError(f"内置 Skill 名称不合法: {name}")
    parse_semver(version)
    if not version_satisfies(__version__, requires_cli):
        raise RuntimeError(
            f"内置 Skill {name} {version} 与当前 CLI {__version__} 不兼容: {requires_cli}"
        )
    if root.name != name or not (root / "SKILL.md").is_file():
        raise RuntimeError(f"内置 Skill 目录不完整: {root}")


def list_bundled_skills() -> list[BundledSkill]:
    """加载当前 CLI 内置的全部 Skill，并复核发行清单中的内容哈希。"""

    with _materialized_resources() as (skills_root, manifest_path):
        if manifest_path.suffix == ".json":
            data = json.loads(manifest_path.read_text(encoding="utf-8"))
            if str(data.get("cli_version")) != __version__:
                raise RuntimeError("内置 Skill 清单与当前 CLI 版本不一致。")
            entries = data.get("skills", [])
        else:
            data = tomllib.loads(manifest_path.read_text(encoding="utf-8"))
            entries = data.get("skills", [])

        result: list[BundledSkill] = []
        for entry in entries:
            name = str(entry["name"])
            version = str(entry["version"])
            requires_cli = str(entry["requires_cli"])
            root = skills_root / str(entry.get("path") or name)
            _validate_skill(name, version, requires_cli, root)
            actual_hash = hash_skill_directory(root)
            expected_hash = entry.get("content_sha256")
            if expected_hash and expected_hash != actual_hash:
                raise RuntimeError(f"内置 Skill 内容哈希不匹配: {name}")
            result.append(
                BundledSkill(
                    name=name,
                    version=version,
                    requires_cli=requires_cli,
                    content_sha256=actual_hash,
                    root=root,
                )
            )
        return result


def get_bundled_skill(name: str) -> BundledSkill:
    """按名称获取内置 Skill，不存在时返回明确错误。"""

    for skill in list_bundled_skills():
        if skill.name == name:
            return skill
    raise KeyError(f"CLI 未内置 Skill: {name}")
