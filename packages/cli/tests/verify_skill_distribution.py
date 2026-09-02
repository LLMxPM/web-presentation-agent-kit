"""文件功能：验证 wheel/sdist 中的内置 Skill、版本清单和内容哈希。"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys
import tarfile
import tomllib
from typing import Any
import zipfile

from wp.skills.catalog import version_satisfies


def _hash_entries(entries: dict[str, bytes]) -> str:
    """按运行时相同规则计算归档中的 Skill 内容哈希。"""

    digest = hashlib.sha256()
    for relative_path in sorted(entries):
        digest.update(relative_path.encode("utf-8"))
        digest.update(b"\0")
        digest.update(entries[relative_path])
        digest.update(b"\0")
    return f"sha256:{digest.hexdigest()}"


def verify_wheel(wheel_path: Path) -> dict[str, Any]:
    """验证 wheel 内含可运行 manifest 和完整 Skill 树。"""

    prefix = "wp/_bundled_skills/web-presentation/"
    with zipfile.ZipFile(wheel_path) as archive:
        names = set(archive.namelist())
        manifest_name = "wp/_bundled_skills/manifest.json"
        required = {manifest_name, f"{prefix}SKILL.md"}
        missing = required - names
        if missing:
            raise SystemExit(f"wheel 缺少 Skill 文件: {sorted(missing)}")
        manifest = json.loads(archive.read(manifest_name))
        metadata_names = [name for name in names if name.endswith(".dist-info/METADATA")]
        if len(metadata_names) != 1:
            raise SystemExit("wheel 中必须恰好包含一份 METADATA。")
        metadata = archive.read(metadata_names[0]).decode("utf-8")
        package_version = next(
            (
                line.removeprefix("Version: ")
                for line in metadata.splitlines()
                if line.startswith("Version: ")
            ),
            None,
        )
        if manifest.get("cli_version") != package_version:
            raise SystemExit("wheel manifest 的 CLI 版本与包版本不一致。")
        entry = next(item for item in manifest["skills"] if item["name"] == "web-presentation")
        content = {
            name[len(prefix) :]: archive.read(name)
            for name in names
            if name.startswith(prefix) and not name.endswith("/")
        }
        if _hash_entries(content) != entry["content_sha256"]:
            raise SystemExit("wheel 内置 Skill 内容哈希不匹配。")
        return manifest


def verify_sdist(sdist_path: Path) -> dict[str, Any]:
    """验证 sdist 保留从源码重新构建 wheel 所需的 Skill 单一源码。"""

    with tarfile.open(sdist_path) as archive:
        names = archive.getnames()
        catalog_names = [name for name in names if name.endswith("/_skill_sources/catalog.toml")]
        if len(catalog_names) != 1:
            raise SystemExit("sdist 必须恰好包含一份 _skill_sources/catalog.toml。")
        catalog_file = archive.extractfile(catalog_names[0])
        if catalog_file is None:
            raise SystemExit("无法读取 sdist Skill catalog。")
        catalog = tomllib.loads(catalog_file.read().decode("utf-8"))
        source_prefix = catalog_names[0].removesuffix("catalog.toml") + "web-presentation/"
        content: dict[str, bytes] = {}
        for name in names:
            if not name.startswith(source_prefix) or not archive.getmember(name).isfile():
                continue
            source_file = archive.extractfile(name)
            if source_file is None:
                raise SystemExit(f"无法读取 sdist Skill 文件: {name}")
            content[name[len(source_prefix) :]] = source_file.read()
    if "SKILL.md" not in content:
        raise SystemExit("sdist 缺少 web-presentation Skill。")
    entry = next(item for item in catalog["skills"] if item["name"] == "web-presentation")
    entry = dict(entry)
    entry["content_sha256"] = _hash_entries(content)
    return {"schema_version": catalog["schema_version"], "skills": [entry]}


def main() -> None:
    """检查指定 dist 目录内唯一的 wheel 和 sdist。"""

    if len(sys.argv) != 2:
        raise SystemExit("用法: verify_skill_distribution.py <dist-dir>")
    dist_dir = Path(sys.argv[1])
    wheels = list(dist_dir.glob("*.whl"))
    sdists = list(dist_dir.glob("*.tar.gz"))
    if len(wheels) != 1 or len(sdists) != 1:
        raise SystemExit("dist 目录必须恰好包含一个 wheel 和一个 sdist。")
    manifest = verify_wheel(wheels[0])
    source_catalog = verify_sdist(sdists[0])
    if manifest.get("schema_version") != source_catalog.get("schema_version"):
        raise SystemExit("wheel manifest 与 sdist catalog 的 schema 版本不一致。")
    if manifest.get("skills") != source_catalog.get("skills"):
        raise SystemExit("wheel manifest 与 sdist Skill catalog/内容不一致。")
    cli_version = str(manifest["cli_version"])
    for entry in manifest["skills"]:
        if not version_satisfies(cli_version, str(entry["requires_cli"])):
            raise SystemExit(
                f"Skill {entry['name']} 的兼容范围不包含 CLI {cli_version}。"
            )


if __name__ == "__main__":
    main()
