"""文件功能：提供 CLI 内置 Agent Skill 的目录、目标解析与安装管理能力。"""

from wp.skills.catalog import BundledSkill, get_bundled_skill, list_bundled_skills

__all__ = ["BundledSkill", "get_bundled_skill", "list_bundled_skills"]

