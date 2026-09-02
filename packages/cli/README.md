# Web Presentation CLI (`wp`)

面向 `web-presentation` AI 演示文稿创作平台的官方命令行与 Agent 工具包。

External API 路径、Scope、错误码、幂等和异步任务语义以主仓 [External Agent API v1 契约](https://github.com/LLMxPM/web-presentation/blob/main/docs/developer/reference/external-agent-api.md) 为准；CLI 命令和参数以本仓 `wp --help` 与 CLI 实施文档为准。

## 安装与快速开始

```bash
# 从 PyPI 安装公开发行版
uv tool install web-presentation-cli
# 或使用 pipx
pipx install web-presentation-cli

# 验证安装
wp --version
wp --help
```

需要 Python 3.11+。如果使用 `uv` 安装后终端找不到 `wp`，运行 `uv tool update-shell` 并重新打开终端。

从源码开发时才需要以下命令，普通用户不需要克隆仓库：

```bash
# 在 agent-kit 仓库根目录安装 CLI
uv pip install -e ./packages/cli
```

登录 Web Presentation 后，进入“账户设置” → “访问令牌 (PAT)”创建令牌，并授权准备操作的工作空间和所需权限。令牌明文只展示一次，不要发送给智能体或写入项目文件。

```bash
# 本地环境；PAT 会在终端中隐藏输入
wp login

# 自建或远程环境；Backend 根地址不要包含 /api/v1
wp login --endpoint https://presentation.example.com

# 检查环境与连通性
wp doctor

# 查看授权的工作空间并切换当前工作空间
wp workspace list
wp workspace use <workspace_id>

# 查看并切换默认 Profile（Profile 保存 Backend 地址、PAT 和默认工作空间）
wp profile list
wp profile use production
```

配置保存在当前用户的 `~/.web-presentation/config.json`。除非用于已妥善保护的无人值守环境，否则不要使用 `--token` 把 PAT 直接放入命令，以免进入 Shell 历史。

## Agent Skill 管理

CLI 内置 `web-presentation` Skill，可离线安装到受支持 Agent。交互式终端省略参数时会按实际安装目录分组选择：共用 `.agents/skills` 的五个兼容 Agent 作为一组，Claude Code 和 Qoder 各自一组；脚本、管道或 JSON 模式必须显式传入参数。

```bash
# 当前用户全局安装
wp skill install --scope global --agent all

# 当前项目安装；默认解析 Git 根目录，也可用 --project-dir 指定
wp skill install --scope project --agent codex --agent qoder

# 状态与卸载
wp skill status --scope global --agent all
wp skill uninstall --scope global --agent all --yes

# 只预览目标，或导出根目录包含 SKILL.md 的通用 ZIP
wp skill install --scope project --agent all --dry-run
wp skill export web-presentation
```

首次使用建议进入智能体将要工作的项目目录，直接运行 `wp skill install`，然后选择 `2. 项目`。项目级安装会进入项目根目录的 `.agents/skills`、`.claude/skills` 或 `.qoder/skills`，不是安装到 Python 包目录。安装后重新加载智能体窗口或新建会话。

目录映射：

| Agent | 项目级 | 全局 |
| --- | --- | --- |
| Codex、Cursor、GitHub Copilot、Gemini CLI、OpenCode | `.agents/skills` | `~/.agents/skills` |
| Claude Code | `.claude/skills` | `~/.claude/skills` |
| Qoder | `.qoder/skills` | `~/.qoder/skills` |

Skill 与 CLI 一起发布，但使用独立版本。`wp skill status` 会识别缺失、过期、较新、不兼容、用户修改和未受管理等状态；普通升级不会覆盖用户修改，`--force` 会先保留同级备份。CLI 升级不会隐式改写已安装 Skill，需要重新运行 `wp skill install` 完成同步。

当前首发版本关系：CLI `0.2.0` 内置 `web-presentation` Skill `1.0.0`，Skill 声明的 CLI 兼容范围为 `>=0.2.0,<0.3.0`。构建时会把这组关系与规范化内容 SHA-256 写入 manifest。

Windsurf 和 WorkBuddy 不属于本地目录安装目标。`wp skill export` 生成的标准 ZIP 可用于 WorkBuddy 等支持本地上传的产品；CLI 不从 URL 或第三方仓库下载 Skill。

## 复制给智能体：协助安装 CLI、登录和 Skill

把下面整段发给当前智能体。智能体可以执行环境检测和安装命令；PAT 只能由用户本人在隐藏输入中填写：

```text
请协助我安装和初步配置 Web Presentation 的 wp CLI 与 web-presentation Skill。请实际检查当前系统和项目环境，再逐步执行，不要只给通用说明。

先识别操作系统、Shell、当前项目根目录和 Python 版本（需要 Python 3.11+），并检查 wp 是否已安装。未安装时优先使用 `uv tool install web-presentation-cli`，没有 uv 但有 pipx 时使用 `pipx install web-presentation-cli`；已安装时只显示版本，不要擅自升级或降级。随后运行 `wp --version` 和 `wp --help` 验证，必要时帮助我修复当前用户 PATH。

登录前先问我使用本地默认服务还是自建/远程 Backend；远程地址末尾不能包含 `/api/v1`。绝对不要让我把 PAT 发到聊天中，也不要读取或展示配置文件中的 token。请运行不带 `--token` 的 `wp login` 或 `wp login --endpoint <Backend根地址>`，让我本人在隐藏输入中粘贴 PAT；如果我无法接管你的终端，就把命令给我自行执行并等待确认。

登录后运行 `wp workspace list`。有多个工作空间时，把不含敏感信息的名称和 ID 给我选择，再执行 `wp workspace use <workspace_id>`，不要猜测。然后运行 `wp doctor` 和 `wp whoami` 验证 Backend、PAT、默认工作空间和权限。

最后为当前智能体安装 Skill，默认使用项目级，并明确实际目录：Codex、Cursor、GitHub Copilot、Gemini CLI、OpenCode 共用项目根目录 `.agents/skills/web-presentation`；Claude Code 使用 `.claude/skills/web-presentation`；Qoder 使用 `.qoder/skills/web-presentation`。如果无法判断当前智能体或安装范围，先问我。使用 `wp skill install --scope project --agent <当前agent>` 安装，并用相同参数运行 `wp skill status`。不要使用 `--force`，除非解释冲突和备份行为后得到我的确认。

完成后汇总 CLI 版本、Backend 地址、默认工作空间名称和 ID、Skill 版本、实际安装目录与状态，并提醒我重新加载智能体窗口或新建会话。任何删除、覆盖、强制安装、降级、卸载或 PAT 吊销操作都必须先征得我的明确同意。
```

更完整的人工操作步骤和排障说明见 [CLI 与 Agent Skill 安装指南](https://github.com/LLMxPM/web-presentation-agent-kit/blob/main/docs/getting-started.md)。

## 常用操作

```bash
wp system health
wp project list
wp project configuration get <project_id>
wp page list --project-id <project_id>
wp page dependencies <page_id>
wp component list --scope suggested --project-id <project_id>
wp asset content get <asset_id>
wp theme list
wp style list
wp job wait <job_id>
```

复杂写入参数使用 `--payload-file`、`--edits-file`、`--content-file`、`--route-file` 和 `--ids-file`。Build、产物下载、Agent 运行、图片能力、Restore 和 MCP 不属于当前 CLI。

叶子命令的 `--help` 会从当前 Profile 的 Backend `/openapi.json` 加载请求参数和完整 Schema；服务不可达时仍返回本地语法帮助，不缓存 Schema。

写入命令支持 `--idempotency-key <key>`；网络超时后需要重放同一业务请求时复用原 key，不要把同一个 key 用于不同请求。
