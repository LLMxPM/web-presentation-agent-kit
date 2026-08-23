# web-presentation-agent-kit

`web-presentation-agent-kit` 是 `web-presentation` 的 CLI 外部 Agent 接入仓库，集中维护：

- `wp` CLI：面向 Shell/桌面 Agent 的确定性命令行能力；
- `web-presentation` Skill：指导 Agent 按工作空间、规范、校验和异步任务流程创作；
- `api-client`：供 CLI 使用的认证、工作空间上下文、幂等、错误和任务轮询客户端。

MCP Server 不在本期范围内。仓库中的 `mcp-server/` 和相关设计文档仅作为后续接入占位，不属于当前 Skill、CLI 文档、默认测试门禁或发布能力；本期不要据此调用或扩展 MCP。

主平台仓库仍是 `web-presentation`，负责 Backend、Editor、Runtime 和 `/api/v1` External API v1。本仓库不直接访问主平台数据库、Redis、Runtime 或 Chromium。

主仓唯一维护的 External API v1 契约：[External Agent API v1 契约](https://github.com/LLMxPM/web-presentation/blob/main/docs/developer/reference/external-agent-api.md)。本仓库只维护 CLI、MCP Server、共享客户端和 Skill 的接入实现。

## 目录

```text
web-presentation-agent-kit/
├── packages/
│   ├── api-client/       # 共用 HTTP 客户端
│   └── cli/              # wp 命令行
├── mcp-server/           # 后续接入占位，本期不纳入范围
├── docs/                 # CLI 能力补齐与接入实施文档
├── skills/
│   └── web-presentation/ # 配套 Agent Skill
├── tests/                # 跨包契约测试
└── pyproject.toml        # uv workspace
```

## 本地开发

要求 Python 3.11+ 和 `uv`：

```powershell
uv sync
uv run --project packages/cli wp --help
uv run pytest
```

安装 CLI：

```powershell
uv tool install --editable packages/cli
wp --help
```

CLI 通过本地 Profile 配置 Backend 地址、PAT 和默认工作空间。对外接口公共前缀固定为 `/api/v1`，不要使用旧的 `/api/external/v1`。

CLI 能力补齐实施文档：[docs/cli-capability-completion.md](docs/cli-capability-completion.md)

## 边界

1. Backend 是权限、工作空间隔离、业务校验和异步任务状态的最终事实源；API 语义以主仓 [External Agent API v1 契约](https://github.com/LLMxPM/web-presentation/blob/main/docs/developer/reference/external-agent-api.md) 为准。
2. CLI 和 Skill 不复制 Backend 内部 AI `tool_specs.py`；CLI 只暴露面向用户可直接执行的资源化命令，平台契约由主仓 External API 文档维护。
3. 写操作必须携带幂等语义；页面、组件和截图等重任务通过 Backend 已有任务接口执行。
4. Build External API 尚未冻结，本期 CLI、共享客户端和 Skill 均不提供构建或产物下载能力。
5. PAT 不得进入 CLI 输出、异常消息、日志或 telemetry。

主仓文档只维护平台契约；CLI 命令、Skill 工作流、适配测试和实施进度只在本仓维护，避免两边同时修改同一份实现说明。

## 发布关系

本期仅发布 CLI；版本发布前必须针对目标 `web-presentation` 版本运行 External API v1 契约测试。

## 公开安装与发布

公开用户可直接从 PyPI 安装 CLI：

```bash
uv tool install web-presentation-cli
# 或
pipx install web-presentation-cli
```

发布流程和 PyPI Trusted Publishing 配置见：[CLI 公开分发](docs/public-distribution.md)。
