# web-presentation MCP Server 详细实施计划

## 1. 文档状态

- 状态：审阅修订版；M0 完成契约审计后作为 `mcp-server/` 的执行基线
- 依据：主仓契约文档 `web-presentation/docs/developer/reference/external-agent-api.md`；MCP 平台侧边界见 `web-presentation/docs/developer/mcp.md`
- 适用范围：本仓 `mcp-server/`、共享包 `packages/api-client/`
- 协作约定：遵循仓库 `AGENTS.md`；公共前缀固定 `/api/v1`；不访问 Backend 数据库、Redis、Runtime、Chromium
- 前置条件：源码分段读取和文件上传输入若无法由 External API 提供，必须先完成主仓契约变更，再进入对应里程碑

本文只维护 agent-kit 侧的 MCP Server 实施：协议、工具/资源 allowlist、请求级认证、结果投影、代码结构、测试和发布。External API 的路径、Scope、DTO、错误码、幂等和 Job 语义不在本文定稿，以主仓 [External Agent API v1 契约](https://github.com/LLMxPM/web-presentation/blob/main/docs/developer/reference/external-agent-api.md) 为唯一事实源。

### 已确认决策

| 决策项 | 结论 |
| :--- | :--- |
| 实施范围 | 先实施 M0～M4；M5 只有在 OAuth/JWKS 能力评审通过后排期 |
| 工作空间上下文 | stdio 允许工具入参 `workspace_id` > 环境变量 `WP_WORKSPACE_ID`；HTTP 必须按请求提供并校验上下文 |
| 规范/指南暴露形态 | Tools + Resources 并存 |
| MVP 认证 | PAT（Bearer），OAuth 在 M5 落地 |
| 首选传输 | stdio + Streamable HTTP 双轨 |
| HTTP 凭证生命周期 | 禁止复用进程级 Token；每个 HTTP 请求独立解析 Bearer 并转发至 Backend |
| 工具设计路线 | 靠近平台内容助手：固定通用业务工具 + 页面/组件重任务专用工具；不按 External API endpoint 一对一暴露 |

## 2. 现状盘点与差距分析

### 2.1 已有能力

- `src/wp_mcp/server.py`：MCPServer 骨架，stdio / streamable-http（stateless + json_response）双入口。
- 已注册只读工具：`wp_list_workspaces`、`wp_get_operation_guide`、`wp_get_standards`、`wp_list_projects`；Resource：`wp://guides`。
- `src/wp_mcp/backend.py`：BackendGateway 经共享 `web-presentation-api-client` 访问 Backend。
- `packages/api-client/` 已具备：Bearer PAT、`X-Workspace-ID`、`Idempotency-Key`、Mutation/Build 任务轮询、二进制下载与跨域 PAT 泄露防护（`CROSS_ORIGIN_PAT_BLOCKED`）。这些能力仍缺少响应 Header/状态元数据、`Retry-After`、网络异常和流式大小限制，必须在 M1 前补齐。

### 2.2 差距

1. 工具覆盖率低：当前 4 个工具；原方案按 endpoint 一对一扩展会达到 43～47 个，工具上下文和模型选择噪声偏大。
2. 错误契约不完整：当前以 `RuntimeError(JSON 字符串)` 抛出，缺少 `code/message/retryable/details` 结构化与可重试判定。
3. 返回无统一信封：缺 `summary/data/request_id` 分层，模型可读性与机器可读性未分离。
4. 缺少护栏：无分页上限、源码截断策略、请求超时配置、响应大小限制；部分 Backend 端点本身也不支持分页或分段读取。
5. HTTP 模式安全缺失：无按请求 Bearer 校验与转发、Origin/Host 校验、限流和日志脱敏。
6. 二进制契约未闭合：截图和资源文件的 MCP 返回形态不同，不能统一按 JSON 或 image content 处理。
7. 通用工具的参数分派未定义：需要以 `resource_type`、`view`、`action`、`mode` 和 `operation_key` 组成稳定判别字段，复杂 payload 按操作手册按需披露。
8. 测试薄弱：仅 1 个 settings 单测；无错误映射、协议、契约、并发隔离、敏感字段脱敏和 E2E 测试。

## 3. 架构与目录演进

保留现有 `wp_mcp` 包名与 `wp-mcp` 入口，按本实施计划演进，并遵守主仓 External API v1 契约：

```text
mcp-server/src/wp_mcp/
├── server.py            # 入口、传输参数、工具/资源/Prompt 注册
├── settings.py          # 扩展：超时、分页/大小上限、轮询上限、日志级别、Origin/Host allowlist
├── auth.py              # 新增：stdio/HTTP 凭证上下文解析与日志脱敏
├── request_context.py   # 新增：按请求保存 Token、workspace 和 request_id，禁止跨请求复用
├── errors.py            # 新增：ApiClientError → MCP 结构化错误映射
├── schemas.py           # 新增：ToolResult 信封、二进制返回和分页/裁剪输入模型
├── gateway/
│   ├── backend.py       # 现 backend.py 演进：统一请求出口与错误转换
│   ├── jobs.py          # Mutation/Build 提交、轮询、取消封装
│   └── binaries.py      # 截图/资源内容的字节获取与 Content-Type 处理
├── tools/
│   ├── bootstrap.py     # 工作空间、whoami、能力矩阵
│   ├── generic.py       # 指南、规范、list/get/create/update/archive/validate/action
│   ├── mutations.py     # 页面/组件专用异步 Job、状态和取消
│   ├── visual.py        # 截图与构建
│   └── assets.py        # 资源上传、文本内容和输入限制
├── resources.py         # wp://guides、wp://standards/{page|component}
└── prompts.py           # M3 后可选创作流程 Prompt
```

每个源文件开头写明中文功能描述，函数补充职责/输入输出/关键约束注释；依赖使用 `uv` 管理。工具注册采用显式 allowlist，不做“扫描路由自动暴露”。工具命名和参数形态参考平台内容助手的通用语义，但不得复制 Backend `tool_specs.py`；具体 External API 参数通过 `/guides` 和 `/standards` 发现并由 MCP 自己的公开契约投影。

## 4. 关键契约设计（M0 冻结项）

### 4.1 workspace_id 与凭证解析规则

- stdio：解析顺序为工具显式参数 `workspace_id` > `Settings.workspace_id`（环境变量）> 抛出结构化错误，提示先调用 `wp_list_workspaces`。当前代码中的 `WP_ENDPOINT`/`WP_TOKEN`/`WP_WORKSPACE_ID` 作为首版兼容命名；若同时提供旧、新别名必须拒绝冲突配置。
- Streamable HTTP：每个请求必须提供 `Authorization: Bearer ...`，MCP Server 按请求解析并转发 Token；不得使用进程级 `WP_TOKEN` 作为远程请求的隐式凭证。HTTP 模式下默认要求工具显式传入 `workspace_id`，不得从进程环境继承。
- `wp_list_workspaces`、`wp_whoami`、`wp_get_operation_guide` 和 `wp_validate_entity` 不需要 MCP 层的工作空间参数；需要对象归属的读写工具仍应显式传递空间上下文，最终权限由 Backend 校验。
- Gateway/API Client 必须按请求接收 Token 和 workspace，不允许使用带固定身份的全局单例；HTTP 并发请求必须通过测试证明不会串用 Token 或 workspace。

### 4.2 返回信封

普通工具返回统一成功信封；错误和二进制结果使用 MCP 原生结果形态：

```json
{
  "summary": "面向模型的一句话摘要",
  "data": { },
  "request_id": "...",
  "truncated": false
}
```

- 普通成功结果通过 MCP 文本内容携带上述 JSON；若 SDK 支持 `structuredContent`，同时写入同一份结构化信封，不允许两份数据语义漂移。
- 普通错误使用 `isError=true`，内容中携带 `code`、`message`、`retryable`、`status_code`、`details` 和可用的 `request_id`；不得仅抛出 JSON 字符串异常。
- 截图使用 MCP Image Content；非图片二进制资源暂不通过 MCP 交付，文本资源按受限文本契约处理。
- 列表工具强制分页：默认 `page=1`，`page_size` 上限 20，超出按上限收敛并在 `summary` 说明。对 Backend 当前未分页的页面/组件版本列表，M0 必须决定是补充 Backend 分页，还是明确限制返回条数并提供按版本号读取。
- 源码/长文本设最大返回字符数（初值 20000），触发截断时置 `truncated=true`。只有 Backend 提供 offset/limit 或分段读取契约时，才能提示“继续读取下一段”；否则只能明确提示结果被截断。
- 所有输入同样受限：源码、编辑列表、JSON 深度、分页参数、Base64 文件和单次请求体必须有独立上限，不能只限制输出。

### 4.3 错误映射

`errors.py` 将 `ApiClientError` 映射为 MCP 工具层结构化错误，字段：`code`、`message`、`retryable`、`status_code`、`details`、`request_id`。MCP 层不得依赖 Backend 错误始终包含统一字段：Backend 当前可能使用 `data` 或 `detail`，适配层必须规范化并限制详情大小。

| Backend 情况 | retryable | MCP 行为 |
| :--- | :--- | :--- |
| 401 | 否 | 未认证；提示检查 PAT，不自动重试 |
| 403 | 否 | 缺少 Scope 或工作空间未授权 |
| 404 | 否 | 对象不存在或不属于当前空间，不泄露存在性 |
| 409 | 否 | 版本冲突/幂等键冲突；提示重新读取最新版本 |
| 429 | 是 | 尊重 `Retry-After` 后有限重试 |
| 5xx/网络失败 | 仅幂等读 | 自动重试一次；写操作不自动重试；需捕获 `httpx` 网络异常 |
| Job 终态失败 | 否 | 原样透传任务业务错误码与诊断摘要 |

`packages/api-client` 在 M1 前必须补充：响应状态码、`X-Request-ID`、`Retry-After` 和 Content-Type 的可用元数据；可配置 connect/read/write/pool timeout；网络异常归一化；带 Content-Length/分块检查的流式二进制读取。429 重试必须尊重服务端等待时间并设置总预算。

### 4.4 幂等键策略

- 写工具由 MCP 层生成 UUID v4 作为 `Idempotency-Key`；同时在返回 `data.idempotency_key` 回传。若 Backend 返回 202、201 或 200，MCP 应保留原始状态语义，不做全局假设。
- 所有写工具提供可选入参 `idempotency_key`，模型重试同一逻辑操作时必须复用回传值。
- 校验接口（POST `/validate/code`）不携带幂等键，与 CLI 行为一致。

## 5. 工具总目录（语义化 Allowlist）

工具不再按 External API endpoint 一对一暴露，而是使用固定通用工具承载资源类型、视图和操作分派。复杂 payload 由 `wp_get_operation_guide` 按 `operation_key` 按需说明；MCP 不复制 Backend 内部 `tool_specs.py`。

目标规模：M1 约 9 个工具；M3 累计约 19 个；M4 累计约 24 个。M3 的恢复/发布扩展动作不默认注册。

### 5.1 工作空间引导、通用读取与校验（M1，9 个）

| 工具 | 主要参数 | Backend 映射 | 备注 |
| :--- | :--- | :--- | :--- |
| `wp_list_workspaces` | 无 | GET `/workspaces` | 启动引导，不需要 workspace |
| `wp_get_workspace` | `workspace_id` | GET `/workspaces/{workspace_id}` | |
| `wp_get_workspace_capabilities` | `workspace_id` | GET `/workspaces/{workspace_id}/capabilities` | 返回 Scope/Operation 能力矩阵 |
| `wp_whoami` | 无 | GET `/auth/whoami` | 任一有效 Token |
| `wp_get_operation_guide` | `operation_key?` | GET `/guides` | 不传 key 返回紧凑索引 |
| `wp_get_code_standards` | `standard_type` | GET `/standards/{page|component}` | 页面或组件规范 |
| `wp_list_entities` | `resource_type`、`filters`、`collection` | 按类型映射 `/projects`、`/projects/{id}/pages`、`/components`、`/assets`、`/themes`、`/styles` | 统一列表/搜索；保留分页护栏 |
| `wp_get_entity` | `resource_type`、`view`、`target_id`、`options` | 按 `view` 映射详情、源码、配置、路由、版本和依赖 endpoint | `view` 必须是固定枚举；M0 冻结每类对象的合法组合 |
| `wp_validate_entity` | `resource_type`、`action=source`、候选源码 | POST `/validate/code` | M1 只承载 page/component 源码校验，不虚构内部预览诊断能力 |

`wp_list_entities` 和 `wp_get_entity` 是上下文控制的关键：列表只返回摘要，源码、配置、路由、版本内容和依赖必须通过 `view` 显式读取，避免一次工具调用灌入完整工作空间。它们的精确请求字段由 External API guides 和 M0 矩阵约束。

### 5.2 通用写入与页面/组件重任务（M3，新增约 10 个）

| 工具 | 主要参数 | Backend 映射 | 备注 |
| :--- | :--- | :--- | :--- |
| `wp_create_entity` | `resource_type`、`mode`、`payload` | 项目/主题/样式的 POST endpoint | M3 先支持 `mode=new`；copy/upload 按需扩展 |
| `wp_update_entity` | `resource_type`、`target_id`、`action`、`payload` | 项目/主题/样式 PATCH endpoint | 只提交用户要求修改的字段 |
| `wp_archive_entity` | `resource_type`、`target_ids` | 各实体 DELETE endpoint | MCP 首批只允许单对象；不暴露批量归档 |
| `wp_execute_action` | `resource_type`、`action`、`target_id`、`payload?` | 首批为 POST `/components/{id}/publish` | 恢复等动作后续按 operation guide 增加 |
| `wp_create_page_job` | 页面创建 payload、`idempotency_key?` | POST `/jobs/mutations/pages` | 页面源码重任务 |
| `wp_apply_page_edits_job` | `page_id`、`base_version_no`、`edits` | POST `/jobs/mutations/pages/edits` | 强制乐观锁 |
| `wp_create_component_job` | 组件创建 payload、`idempotency_key?` | POST `/jobs/mutations/components` | 组件源码重任务 |
| `wp_apply_component_edits_job` | `component_id`、版本/hash、`edits` | POST `/jobs/mutations/components/edits` | 强制乐观锁 |
| `wp_get_mutation_job` | `job_id`、`wait?` | GET `/jobs/mutations/{job_id}` | 状态使用 page/component read Scope |
| `wp_cancel_mutation_job` | `job_id` | POST `/jobs/mutations/{job_id}/cancel` | 使用对应 write Scope |

通用写入工具只覆盖低分支、可由操作手册稳定描述的对象；页面/组件源码仍使用专用 Job 工具，保留精确 Schema、版本锁、异步受理和校验结果，避免把大型源码 payload 塞进一个过宽的通用工具。

### 5.3 视觉复核、构建任务与资源读取（M4，新增约 5 个）

| 工具 | 主要参数 | Backend 映射 | 备注 |
| :--- | :--- | :--- | :--- |
| `wp_get_latest_screenshot` | `page_id`、`workspace_id` | GET `/pages/{id}/screenshot` | 需要 `page:read + preview:run`，返回 Image Content |
| `wp_start_build` | `project_id`、`base_url`、`wait?` | POST `/projects/{id}/builds` | 异步任务 |
| `wp_get_build_status` | `job_id`、`wait?` | GET `/builds/{job_id}` | 只返回任务状态和必要元数据，不返回下载/存储字段 |
| `wp_upload_asset` | 受限 Base64/Resource 输入、元数据 | POST `/assets`（multipart） | 禁止无约束读取本地路径 |
| `wp_get_asset_content` | `asset_id`、`format?` | GET `/assets/{id}/content` | M4 先支持文本；其他二进制等待安全交付契约 |

构建任务只提供受理和状态查询；本期不提供产物下载或交付。

### 5.4 Resources 与 Prompts

- Resources（M1）：`wp://guides`、`wp://standards/page`、`wp://standards/component`；内容按需读取，不自动拼入每轮工具上下文。
- Prompts（M3 后可选）：`create-page-workflow`、`validate-and-fix`。Prompts 仅描述流程，不保存 Token 和平台业务数据副本。

## 6. 里程碑任务分解与验收

### M0 契约审计与方案冻结（1～2 人日，不含主仓改造）

- T0.1 输出 External API 矩阵：工具、HTTP 方法/path、必需 Header、Scope、请求 DTO、响应 DTO、状态码、`X-Request-ID`、分页/大小限制和错误字段。
- T0.2 冻结 stdio 与 HTTP 两套凭证生命周期；完成按请求 Gateway/API Client 设计，禁止进程级 Token 串请求。
- T0.3 冻结普通文本、结构化错误、图片和受限文本资源契约。
- T0.4 明确主仓阻塞项：源码/版本分段读取、版本列表分页、文件上传输入形态。
- T0.5 本计划与主仓 External API v1 契约、agent-kit README 的环境变量命名完成同步。
- 验收：矩阵和阻塞项清单评审通过；External API 需要改动时先建立主仓契约任务，不以“无 API 变更”为默认前提。

### M1 只读校验 MVP 补齐（6～10 人日）

- T1.1 先扩展 `packages/api-client`：响应元数据、请求级 Token、可配置 timeout、网络异常、`Retry-After`、request_id 和受限流式读取；再新增 `errors.py`、`schemas.py`，重构 `server._call`。
- T1.2 实现 9 个 M1 工具：工作空间引导、`wp_get_operation_guide`、`wp_get_code_standards`、`wp_list_entities`、`wp_get_entity` 和 `wp_validate_entity`。
- T1.3 为 `wp_list_entities` 建立 resource_type 到 External API 列表 endpoint 的显式映射，并统一分页/摘要字段。
- T1.4 为 `wp_get_entity` 建立 resource_type + view 的合法组合矩阵，源码、配置、路由、版本和依赖按需读取。
- T1.5 `wp_validate_entity` 先接入 page/component 源码校验；不把平台内部 `validate_entity` 的预览诊断能力未经 External API 契约直接暴露。
- T1.6 注册 `wp://standards/page`、`wp://standards/component` Resources。
- T1.7 单元测试：错误映射表全分支、按请求 Token/workspace 注入与冲突拒绝、通用工具判别字段、resource_type/view 合法组合、信封结构与截断标记、各 gateway 方法路径拼接正确性、版本列表边界。
- T1.8 协议冒烟测试：基于 mcp SDK 内存客户端完成 `initialize`、`tools/list`、`tools/call`、`resources/read` 断言。
- 验收：stdio 下 Inspector 可连接并调用全部 M1 工具；Token 缺失/403/404 场景返回稳定错误码。

### M2 远程接入加固（3～5 人日）

- T2.1 Streamable HTTP 安全：按请求强制 Bearer 校验（拒绝匿名）、`Origin`/`Host` allowlist 校验防 DNS rebinding；不得回退到服务端环境 Token。
- T2.2 日志脱敏（Authorization、PAT 不落盘），注入 request_id；限流第一版由反向代理承担，进程内令牌桶列为可选。
- T2.3 通过自定义 ASGI 包装或 SDK 支持方式提供 `/healthz` 健康端点（进程自检，不代理 Backend）；明确 `/mcp` 的 Accept、GET、POST、断开重连和协议版本行为。
- T2.4 契约测试：`httpx.MockTransport` 固化路径、Header、幂等键、分页参数行为；同时使用主仓 OpenAPI/契约快照或 dev Backend，避免把 Mock 当成 Backend 变更检测。
- T2.5 编写 Claude Desktop / Cursor / MCP Inspector 接入手册（更新 `mcp-server/README.md`）。
- T2.6 并发隔离测试：两个不同 Bearer 和 workspace 的 HTTP 请求并发执行，验证 Token、Header、日志和结果不串线。
- 验收：HTTPS 下远程客户端连接成功；跨域 Origin 被拒；匿名请求返回 401 结构化错误；HTTP 请求不依赖 `WP_TOKEN`。

### M3 受控写入与异步任务（6～10 人日）

- T3.1 `gateway/jobs.py`：提交、轮询、取消封装；等待策略默认受理即返回，可选 `wait=true`（≤60s，复用 api-client 轮询）。超时返回当前任务状态和 `job_id`，不要把后台仍在执行的任务伪装成失败。
- T3.2 页面/组件四个专用写入 Job 工具接入，强制乐观锁字段说明与传递。
- T3.3 `wp_create_entity`、`wp_update_entity`、`wp_archive_entity` 和 `wp_execute_action` 接入项目/主题/样式元数据、单对象归档和组件发布；batch-archive 不暴露。
- T3.4 通用写工具的 operation_key、resource_type、action 和 payload 分派测试，确保只走已登记 External API 操作。
- T3.5 幂等键生成/复用链路测试；页面/组件 Mutation 的 202、项目/主题/样式的 200/201 分别测试；取消语义测试。
- T3.6 联调 E2E：创建页面 Job → 轮询至终态 → 用旧版本再次编辑 → 验证 409 版本冲突映射。
- 同步义务：若实现中发现 DTO/错误码/异步语义缺口，按 AGENTS.md 要求同步主仓契约测试后再继续。
- 验收：写入链路具备幂等重试与乐观锁冲突处理；Job 失败原样透传业务错误码。

### M4 视觉复核、构建任务与资源读取（5～8 人日）

- T4.1 `gateway/binaries.py`：截图/资源内容的流式字节获取、Content-Type 断言、Content-Length/实际大小阈值和内容类型白名单。
- T4.2 `wp_get_latest_screenshot`：拉取 PNG 后以 MCP image content（base64）返回；超过阈值拒绝并建议改用 CLI，工具本身不承担 CLI 的本地文件写入行为。
- T4.3 `wp_start_build` / `wp_get_build_status`：受理+可选等待；轮询时长上限。
- T4.4 `wp_upload_asset` / `wp_get_asset_content`：按 M0 冻结的输入/输出形态执行；M4 先支持文本资源。
- 验收：“生成→校验→截图→构建任务状态查询”闭环在 Inspector 与至少一个真实客户端跑通。

### M5 OAuth 与生态化（8～15 人日，条件性）

- T5.0 前置：向主仓提出 OAuth/JWKS 能力需求清单并评审（账户系统若无 OAuth 能力需单独排期）。
- T5.1 Resource Server 能力：RFC 9728 Protected Resource Metadata 端点、WWW-Authenticate challenge、audience/resource 校验。
- T5.2 stdio 保持 PAT 不变；HTTP 双轨支持 PAT 手工配置与 OAuth 标准授权。
- T5.3 审计日志字段：request_id、用户、Token public id、工作空间、工具名、目标对象、结果状态、耗时；失败告警钩子。
- T5.4 多客户端回归矩阵：Claude Desktop、Cursor、MCP Inspector（及当期支持的远程客户端）。
- 验收：至少两种真实客户端完成授权与创作闭环；异常调用与越权尝试有审计记录。

## 7. 测试计划与验证命令

| 类型 | 内容 | 执行 |
| :--- | :--- | :--- |
| 单元 | 错误映射、workspace 注入、信封/截断、幂等键、路径拼接 | `uv run --project mcp-server pytest` |
| 协议 | initialize/tools/list/tools/call/resources/read/prompts | mcp SDK 内存客户端测试 |
| 契约 | MockTransport 固化请求形态；主仓 OpenAPI/契约快照和 dev Backend 验证 External API 变化 | `uv run pytest` + 主仓契约命令 |
| 安全 | 匿名/过期/吊销 Token、Scope 缺失、跨空间 ID、Origin/Host 校验、并发凭证隔离、日志脱敏 | 单测 + E2E + 手工清单 |
| E2E | M3/M4 创作闭环、版本冲突、跨空间拒绝 | 联调 dev 环境 |
| 回归 | CLI 依赖的 api-client 行为不回归 | `uv run --project packages/cli wp --help` 及 CLI 测试 |

## 8. 依赖主仓协作事项

1. 截图形态确认：当前 External API 为 PAT 保护直出 PNG；MCP 使用 image content，需验证同步排队耗时和客户端兼容性。
2. M5 前置：OAuth Authorization Server / JWKS 能力评估与接口需求评审。
3. 源码与版本接口是否支持分段读取/分页；若不支持，MCP 只能做有界截断，不能承诺继续读取。
4. `wp_upload_asset` 的 MCP 输入形态、最大大小、类型白名单和远程客户端兼容性。
5. `/guides` 是否补充公开请求 DTO Schema；若不补充，由 agent-kit 维护人工评审的 MCP Schema 投影。
6. External API v1 路径、Scope、DTO、错误码或异步任务语义变化时，双向同步契约测试。

## 9. 风险与开放问题

- 图片 image content 在不同 MCP Client 的展示兼容性需实测（M4 内验证）。
- `stateless_http=True` 只解决协议会话状态，不解决凭证上下文；必须使用请求级 Token/workspace 上下文，不能用全局 Gateway。
- 限流责任边界：优先反向代理；若裸部署需补进程内限流。
- 大型工作空间的列表规模依赖分页护栏，必要时推动 Backend 侧筛选参数增强。

## 10. 工作量汇总

| 里程碑 | 估算 |
| :--- | ---: |
| M0 契约审计与方案冻结 | 1～2 人日 |
| M1 只读校验 MVP 补齐 | 6～10 人日 |
| M2 远程接入加固 | 3～5 人日 |
| M3 受控写入与异步任务 | 6～10 人日 |
| M4 视觉复核、构建任务与资源读取 | 5～8 人日 |
| M5 OAuth 与生态化（条件性，另计） | 8～15 人日 |
| M0～M4 合计（不含主仓契约改造） | 约 21～35 人日 |
