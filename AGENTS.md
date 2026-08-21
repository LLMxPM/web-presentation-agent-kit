# AGENTS.md

## 仓库定位

`web-presentation-agent-kit` 是 `web-presentation` 的外部 Agent 接入仓库。它维护 CLI、MCP Server、共享 API Client 和配套 Skill，不承载 Backend、Editor、Runtime 或平台数据库。

## 基础规范

- 使用中文进行协作、提交说明和文档编写。
- Python 项目使用 `uv` 管理依赖，使用 `.venv` 管理虚拟环境。
- 新增 Python 源文件开头写明文件功能描述；Markdown 文件不需要。
- 函数补充中文注释，优先说明职责、输入输出和关键约束。
- 外部 HTTP 公共前缀固定为 `/api/v1`，禁止重新引入 `/api/external/v1`。
- 不要在 CLI/MCP 中直接访问 Backend 数据库、Redis、Runtime、Chromium 或内部 Service。
- 不要复制 Backend `tool_specs.py` 的内部工具目录；通过 External API v1 的 guides、standards 和资源接口发现契约。

## 模块边界

- `packages/api-client/`：只负责 HTTP、PAT、工作空间 Header、幂等 Header、错误和任务轮询；不包含 Click 或 MCP 协议代码。
- `packages/cli/`：负责 `wp` 命令解析、Profile 配置和终端输出；通过 `api-client` 调 Backend。
- `mcp-server/`：负责 MCP Tools/Resources/Prompts、传输和结果格式化；通过 `api-client` 调 Backend。
- `skills/`：只描述 Agent 的工作流、检查点和安全边界，不保存 Token，不内置平台业务数据副本。

## 验证

```powershell
uv run pytest
uv run --project packages/cli wp --help
```

涉及 External API v1 路径、Scope、DTO、错误码或异步任务语义变化时，应同步更新主仓 `web-presentation` 的契约测试和本仓的适配测试。
