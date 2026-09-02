"""文件功能：为 CLI 构建映射共享 API Client，并打包带版本清单的官方 Skill。"""

from __future__ import annotations

from pathlib import Path
import hashlib
import json
import shutil
import tempfile
import tomllib
from typing import Any

from hatchling.builders.hooks.plugin.interface import BuildHookInterface


class CustomBuildHook(BuildHookInterface):
    """把同仓 API Client 与顶层 Skill 单一源码映射到 CLI 发行物。"""

    _temporary_directory: Path | None = None

    def _find_skills_root(self) -> Path:
        """定位仓库源码或已进入 sdist 的 Skill 源目录。"""

        repository_root = Path(self.root).parents[1]
        candidates = [repository_root / "skills", Path(self.root) / "_skill_sources"]
        for candidate in candidates:
            if (candidate / "catalog.toml").is_file():
                return candidate
        raise RuntimeError("无法定位 skills/catalog.toml，不能构建 CLI Skill 资源。")

    def _find_api_client_source(self) -> Path:
        """定位同仓源码或已进入 sdist 的共享 API Client 包。"""

        candidates = [
            Path(self.root).parent / "api-client" / "src" / "wp_api_client",
            Path(self.root) / "src" / "wp_api_client",
        ]
        for candidate in candidates:
            if (candidate / "__init__.py").is_file():
                return candidate
        raise RuntimeError("无法定位 wp_api_client，不能构建 CLI 发行物。")

    @staticmethod
    def _hash_skill_directory(root: Path) -> str:
        """使用与运行时一致的路径和内容规则计算 Skill SHA-256。"""

        digest = hashlib.sha256()
        files = sorted(
            (
                (path.relative_to(root).as_posix(), path)
                for path in root.rglob("*")
                if path.is_file() and path.name != ".wp-install.json"
            ),
            key=lambda item: item[0],
        )
        for relative_path, path in files:
            digest.update(relative_path.encode("utf-8"))
            digest.update(b"\0")
            digest.update(path.read_bytes())
            digest.update(b"\0")
        return f"sha256:{digest.hexdigest()}"

    def _create_manifest(self, skills_root: Path) -> Path:
        """生成包含 CLI/Skill 版本关系和内容哈希的临时发行清单。"""

        catalog = tomllib.loads((skills_root / "catalog.toml").read_text(encoding="utf-8"))
        entries: list[dict[str, str]] = []
        for item in catalog.get("skills", []):
            source_path = skills_root / str(item["path"])
            entries.append(
                {
                    "name": str(item["name"]),
                    "version": str(item["version"]),
                    "path": str(item["path"]),
                    "requires_cli": str(item["requires_cli"]),
                    "content_sha256": self._hash_skill_directory(source_path),
                }
            )
        self._temporary_directory = Path(tempfile.mkdtemp(prefix="wp-skill-build-"))
        manifest_path = self._temporary_directory / "manifest.json"
        manifest_path.write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "cli_version": str(self.metadata.version),
                    "skills": entries,
                },
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        return manifest_path

    def initialize(self, version: str, build_data: dict[str, Any]) -> None:
        """按构建目标注入 API Client、Skill 源码和生成的发行清单。"""

        skills_root = self._find_skills_root()

        if self.target_name == "sdist":
            force_include = build_data.setdefault("force_include", {})
            force_include[str(skills_root / "catalog.toml")] = "_skill_sources/catalog.toml"
            for item in tomllib.loads(
                (skills_root / "catalog.toml").read_text(encoding="utf-8")
            ).get("skills", []):
                path = str(item["path"])
                force_include[str(skills_root / path)] = f"_skill_sources/{path}"
            return

        manifest_path = self._create_manifest(skills_root)
        force_include = build_data.setdefault("force_include", {})
        force_include[str(manifest_path)] = "wp/_bundled_skills/manifest.json"
        for item in tomllib.loads(
            (skills_root / "catalog.toml").read_text(encoding="utf-8")
        ).get("skills", []):
            path = str(item["path"])
            force_include[str(skills_root / path)] = f"wp/_bundled_skills/{path}"

        api_client_source = self._find_api_client_source()
        if version != "editable":
            force_include[str(api_client_source)] = "wp_api_client"
            return

        editable_include = build_data.setdefault("force_include_editable", {})
        editable_include[str(api_client_source)] = "wp_api_client"

    def finalize(self, version: str, build_data: dict[str, Any], artifact_path: str) -> None:
        """构建完成后清理仅用于生成内置 manifest 的临时目录。"""

        if self._temporary_directory is not None:
            shutil.rmtree(self._temporary_directory, ignore_errors=True)
            self._temporary_directory = None
