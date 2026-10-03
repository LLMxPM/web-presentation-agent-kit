# AGENTS.md

## 仓库定位

`web-presentation-agent-kit` 是 `web-presentation` 的外部 Agent 接入仓库。当前可交付范围为 `wp` CLI、共享 API Client 和配套 Skill，不承载 Backend、Editor、Runtime 或平台数据库。2026-10-03 已按用户要求恢复远程多用户 MCP 规划，工作包见 [MCP 实施计划](docs/mcp-implementation-plan.md)；当前仅落计划，历史骨架不代表可用能力。正式实现启动时再同步相应开发与验证门禁。

## 基础规范

- 使用中文进行协作、提交说明和文档编写。
- Python 项目使用 `uv` 管理依赖，使用 `.venv` 管理虚拟环境。
- 新增 Python 源文件开头写明文件功能描述；Markdown 文件不需要。
- 函数补充中文注释，优先说明职责、输入输出和关键约束。
- 外部 HTTP 公共前缀固定为 `/api/v1`。
- 不要在 CLI 中直接访问 Backend 数据库、Redis、Runtime、Chromium 或内部 Service。
- 不要复制 Backend `tool_specs.py` 的内部工具目录；以 External API v1 契约、standards 和资源接口为准。
- 已授权的 MCP 规划以实施计划维护；后续按用户明确启动的工作包开发。未完成验收前，不把 MCP 作为当前可用入口写入 Skill 或用户文档。

## 模块边界

- `packages/api-client/`：只负责 CLI 使用的 HTTP、PAT、工作空间 Header、幂等 Header、错误和任务轮询；不包含 Click 或协议层代码。
- `packages/cli/`：负责 `wp` 命令解析、Profile 配置和终端输出；通过 `api-client` 调 Backend。
- `mcp-server/`：远程多用户方案待实施，协议、传输、安全和任务边界见实施计划；当前历史骨架不纳入正式发布范围，实施时补齐对应测试门禁。
- `skills/`：只描述 CLI Agent 的工作流、检查点和安全边界，不保存 Token，不内置平台业务数据副本。

## 验证

```powershell
uv run pytest packages/api-client/tests packages/cli/tests
uv run --project packages/cli wp --help
```

根仓 `uv run pytest` 仍可用于全量回归，但历史 `mcp-server/tests` 尚不足以作为远程 MCP 交付门禁。规划阶段可维护 MCP 文档；进入实现阶段后，按实施计划补齐协议、身份隔离和真实 HTTP 测试，并将它们纳入对应 CI，不能只依赖工具名称检查。

涉及 External API v1 路径、Scope、DTO、错误码或异步任务语义变化时，应同步更新主仓 `web-presentation` 的契约测试和本仓的适配测试。


## 契约失败语义

CLI 契约叶子帮助仅在当前 Backend OpenAPI 及全部请求引用解析成功后输出；失败立即退出 1，不保留部分帮助、离线 Schema 或缓存。Doctor 必须独立检查注册表派生的全部契约，有 error 时退出 1。新增命令不得维护第二份契约清单。
