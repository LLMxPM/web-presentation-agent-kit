# AGENTS.md

## 仓库定位

`web-presentation-cli` 维护官方 `wp` CLI、仓内专用同步 API Client 与配套 Skill，继承原 `web-presentation-agent-kit` 的 Git 历史与 Apache-2.0 协议。MCP 代码、异步客户端、实施规划和服务交付已拆到 [web-presentation-mcp](https://github.com/LLMxPM/web-presentation-mcp)。本仓不承载 MCP、Backend、Editor、Runtime 或平台数据库。

## 基础规范

- 使用中文进行协作、提交说明和文档编写。
- Python 项目使用 `uv` 管理依赖，使用根 `.venv` 管理虚拟环境。
- 源文件开头写明文件功能描述；Markdown 文件不需要。
- 函数补充中文注释，优先说明职责、输入输出和关键约束。
- 文件职责过多时拆分模块；不要为了拆仓重构无关功能。
- 外部 HTTP 公共前缀固定为 `/api/v1`。
- CLI 不直接访问 Backend 数据库、Redis、Runtime、Chromium 或内部 Service。
- 不复制 Backend `tool_specs.py` 的内部工具目录；以 External API v1、OpenAPI、standards 和资源接口为准。
- CLI 保留同步调用。MCP 自行维护异步客户端，不依赖本仓客户端或 `wp`；允许小规模传输适配重复，不发布共享 SDK。

## 模块边界

- `packages/api-client/`：CLI 专用同步 HTTP、PAT、工作空间 Header、幂等、错误和任务轮询；随 CLI 打包，不单独发布，不包含 Click 或 MCP。
- `packages/cli/`：`wp` 命令解析、Profile、终端输出与本地文件流程。
- `skills/`：CLI Agent 工作流、检查点和安全边界；不保存 Token 或平台业务数据副本。
- `docs/`：CLI 安装、能力和发布文档。远程 MCP 实施计划只在 MCP 仓库维护。

## 验证

```powershell
uv sync --all-packages --frozen
uv run pytest packages/api-client/tests packages/cli/tests
uv run --project packages/cli wp --help
uv build --package web-presentation-cli --out-dir .tmp/dist
uv run python packages/cli/tests/verify_skill_distribution.py .tmp/dist
```

External API v1 路径、Scope、DTO、错误码或任务语义变化时，联动主仓契约与本仓适配测试。跨仓契约测试需取得明确的主仓版本；相邻主仓缺失导致 skip 时必须报告，不能当作发布验证通过。CLI 拆仓不改变 `wp`、PyPI 包名和已发布版本；后续发布前更新 PyPI Trusted Publisher 的仓库身份，见 [CLI 公开分发](docs/public-distribution.md)。

## 契约失败语义

CLI 契约叶子帮助仅在当前 Backend OpenAPI 及全部请求引用解析成功后输出；失败立即退出 1，不保留部分帮助、离线 Schema 或缓存。Doctor 必须独立检查注册表派生的全部契约，有 error 时退出 1。新增命令不得维护第二份契约清单。
