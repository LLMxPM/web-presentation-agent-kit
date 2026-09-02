# CLI 与 Agent Skill 安装指南

本指南帮助首次使用 Web Presentation 的用户完成三件事：安装 `wp` CLI、登录并选择工作空间、为当前智能体安装 `web-presentation` Skill。

## 准备条件

- Python 3.11 或更高版本；
- Web Presentation 平台账号；
- 一个已授权目标工作空间的个人访问令牌 (PAT)；
- 能执行本地终端命令并支持 Skill 的智能体。

支持的智能体包括 Codex、Cursor、GitHub Copilot、Gemini CLI、OpenCode、Claude Code 和 Qoder。Windsurf 暂不支持；WorkBuddy 可使用标准 ZIP 手动导入。

## 推荐：让智能体协助安装

把下面整段提示词复制给准备使用的智能体。智能体可以完成环境检查、CLI 安装和 Skill 安装；涉及 PAT 时，必须由你本人在隐藏输入的终端提示中填写。

```text
请协助我安装和初步配置 Web Presentation 的 wp CLI 与 web-presentation Skill。请实际检查当前系统和项目环境，再逐步执行，不要只给我一份通用说明。

请遵循以下要求：

1. 先识别操作系统、当前 Shell、当前项目根目录，以及 Python 版本。wp CLI 需要 Python 3.11+。
2. 检查 wp 是否已经安装：
   - 未安装时，优先使用 `uv tool install web-presentation-cli`；
   - 如果系统没有 uv，但有 pipx，可以使用 `pipx install web-presentation-cli`；
   - 不要从源码仓库安装，除非我明确要求开发模式；
   - 已安装时先显示版本，不要擅自升级或降级。
3. 运行 `wp --version` 和 `wp --help` 验证 CLI。如果命令不在 PATH，帮助我修复当前用户的 PATH，并说明是否需要重新打开终端。
4. 配置登录前，先问我使用本地默认服务还是自建/远程服务。远程服务只需要 Backend 根地址，末尾不能包含 `/api/v1`。
5. 绝对不要让我把个人访问令牌 (PAT) 发到聊天中，也不要读取、打印或展示 `~/.web-presentation/config.json` 的 token。请运行不带 `--token` 的 `wp login`，或运行 `wp login --endpoint <Backend根地址>`，让我本人在隐藏输入提示中粘贴 PAT。如果当前工具无法让我接管终端输入，就把这条命令单独给我执行并等待我确认结果。
6. 登录成功后运行 `wp workspace list`。如果只有一个授权工作空间，确认它已成为默认值；如果有多个，请展示不含敏感信息的名称和 ID，让我选择后执行 `wp workspace use <workspace_id>`，不要替我猜。
7. 运行 `wp doctor` 和 `wp whoami`，确认 Backend、PAT、默认工作空间与权限正常。不得在回复中泄露凭证。
8. 为当前智能体安装 Skill。默认采用项目级安装，并明确告诉我它会安装到项目根目录的 Skill 目录：
   - Codex、Cursor、GitHub Copilot、Gemini CLI、OpenCode 共用 `.agents/skills/web-presentation`，只安装一份；
   - Claude Code 使用 `.claude/skills/web-presentation`；
   - Qoder 使用 `.qoder/skills/web-presentation`。
   如果当前智能体或安装范围无法可靠判断，先问我；只有我明确希望所有项目共用时才改用 global。
9. 使用明确的非交互命令安装，例如 `wp skill install --scope project --agent <当前agent>`；随后用相同 scope 和 agent 运行 `wp skill status`。不要使用 `--force`，除非发现冲突、解释备份行为并获得我的确认。
10. 安装完成后汇总：wp CLI 版本、Backend 地址、默认工作空间名称和 ID、Skill 版本、实际安装目录与状态。提醒我重新加载智能体窗口或新建会话，以便发现 Skill。

遇到错误时先诊断原因。任何删除、覆盖、强制安装、降级、卸载或 PAT 吊销操作都必须先征得我的明确同意。
```

### 使用提示词前需要知道什么

智能体通常需要向你确认两个选择：

1. Backend 地址：本地部署默认是 `http://127.0.0.1:8000`；远程环境使用管理员提供的根地址，不附加 `/api/v1`。
2. 安装范围：推荐 `project`，只对当前项目生效；确实希望所有项目都能使用时再选 `global`。

PAT 不应出现在聊天记录里。智能体运行 `wp login` 后，如果你无法接管它的终端输入，请在自己的终端执行智能体给出的登录命令，完成后只回复“登录成功”或提供脱敏错误信息。

## 手动安装

### 1. 安装 CLI

推荐使用 `uv`：

```bash
uv tool install web-presentation-cli
wp --version
```

也可以使用 `pipx`：

```bash
pipx install web-presentation-cli
wp --version
```

如果使用 `uv` 后找不到 `wp`，运行 `uv tool update-shell`，然后重新打开终端。

### 2. 创建 PAT 并登录

登录 Web Presentation，在“账户设置” → “访问令牌 (PAT)”中创建令牌。请选择准备操作的工作空间和所需读写权限，并立即复制只展示一次的明文令牌。

本地默认服务：

```bash
wp login
```

自建或远程服务：

```bash
wp login --endpoint https://presentation.example.com
```

终端提示时再粘贴 PAT。不要为了方便把令牌写进聊天、脚本或项目文件。

### 3. 选择工作空间并诊断

```bash
wp workspace list
wp workspace use <workspace_id>
wp doctor
wp whoami
```

### 4. 安装 Skill

在目标项目内运行交互安装：

```bash
wp skill install
```

范围选择如下：

```text
1. 全局：用户目录下的 Agent Skill 目录
2. 项目：项目根目录下的 Agent Skill 目录（推荐）
```

项目级目录映射：

| 兼容目标 | 项目级目录 | 全局目录 |
| --- | --- | --- |
| Codex、Cursor、GitHub Copilot、Gemini CLI、OpenCode | `.agents/skills/web-presentation` | `~/.agents/skills/web-presentation` |
| Claude Code | `.claude/skills/web-presentation` | `~/.claude/skills/web-presentation` |
| Qoder | `.qoder/skills/web-presentation` | `~/.qoder/skills/web-presentation` |

前五个 Agent 共用 `.agents/skills` 兼容目录，只会安装一份 Skill。也可使用明确的非交互命令：

```bash
# 只安装当前 Agent；把 codex 替换为 cursor、copilot、gemini、opencode、claude 或 qoder
wp skill install --scope project --agent codex
wp skill status --scope project --agent codex

# 同时覆盖三个实际兼容目录
wp skill install --scope project --agent all
wp skill status --scope project --agent all
```

项目目录默认取当前 Git 根目录；不在 Git 仓库中时取当前目录，也可通过 `--project-dir PATH` 明确指定。

安装完成后重新加载智能体窗口或新建会话。CLI 不会自动修改 Agent 配置或重启 Agent。

## 安装后的第一个任务

新会话中可以这样确认 Skill 和 CLI 已被正确使用：

```text
请使用 web-presentation Skill 和 wp CLI，先以只读方式运行环境诊断，确认当前身份、默认工作空间和可用项目。不要进行任何写入，也不要展示 PAT。最后告诉我 CLI 与 Skill 是否就绪，以及我可以选择哪些项目开始创作。
```

## 更新与问题处理

升级 CLI 后需要显式同步 Skill：

```bash
uv tool upgrade web-presentation-cli
wp skill install --scope project --agent all
wp skill status --scope project --agent all
```

安装器默认不会覆盖被用户修改或未受管理的目录。只有确认需要替换时才使用 `--force`；原目录会先移动为同级备份。

常见检查：

```bash
wp doctor
wp profile list
wp workspace list
wp skill status --scope project --agent all
```

配置文件位于 `~/.web-presentation/config.json`，其中包含敏感 PAT。排障时不要把完整文件发送给他人，也不要提交到仓库。
