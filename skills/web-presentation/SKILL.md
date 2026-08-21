---
name: web-presentation
description: Use the web-presentation External API v1 through wp CLI or MCP to create, inspect, validate, and build presentation pages and components while preserving workspace and async-job boundaries.
---

# Web Presentation

在用户要求创建、修改、检查或构建演示页面、组件、资源、主题和样式时使用本 Skill。它只指导 Agent 调用 `web-presentation-agent-kit`，不替代用户的设计判断，也不直接访问平台内部服务。

## 工作流

1. 先确定唯一工作空间。通过 `wp auth whoami`、`wp workspace list` 或等价 MCP Tool 获取授权空间、当前 Scope 和能力；没有明确空间时不要写入。
2. 在生成或修改源码前读取当前 `/api/v1/standards/page`、`/api/v1/standards/component` 和 `/api/v1/guides`。规范和操作手册以 Backend 返回为准，不复制旧提示词或内部 `tool_specs.py`。
3. 先读取目标项目、页面或组件的当前版本和源码，再基于版本基线提交变更。写操作使用 `wp` 或 MCP 的资源化接口，保持幂等键和工作空间上下文。
4. 页面和组件的创建、源码编辑、截图和构建都是异步任务：提交后轮询任务终态，失败时保留 Backend 的错误码和诊断摘要，不假装同步成功。
5. 写入后执行代码校验；需要视觉确认时获取最新截图并检查布局、溢出、可读性和资源加载，再决定是否迭代。需要交付包时最后触发项目构建并确认产物状态。

## 不可违反的边界

- 对外 HTTP 公共前缀固定为 `/api/v1`，禁止使用旧的 `/api/external/v1`。
- 工作空间不是可选的安全提示，而是所有资源查询和写入的隔离边界；不得跨空间猜测、复制或写入资源。
- 不执行永久删除，不绕过 Backend 权限、Schema 校验、版本校验或任务队列。
- 不把 PAT 写入源码、Skill 输出、工具返回、错误消息、日志、截图 URL 或 MCP Resource URI。
- 不直接访问数据库、Redis、Runtime、Chromium 或 Backend 内部 Service。
- 用户只要求说明或检查时保持只读，不主动创建、修改、构建或发布资源。

## 输出习惯

优先输出稳定的 JSON 或结构化结果，说明 `workspace_id`、目标 ID、版本基线、任务 ID 和最终状态。对长源码、图片和构建包使用文件或受保护的短期资源链接，不把大内容塞进普通对话。
