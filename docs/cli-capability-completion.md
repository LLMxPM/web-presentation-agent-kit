# CLI 能力补齐落地实施文档

## 1. 文档信息

- 适用仓库：`web-presentation-agent-kit`
- 关联主仓：`web-presentation`
- 目标模块：`packages/cli`、`packages/api-client`、External API v1 契约测试
- 文档状态：实施基线
- 实施原则：先补 External API v1 已具备且风险可控的能力，再扩展高风险批量和交付能力

本文只维护 agent-kit 侧的 CLI 命令、模块、适配实现、测试和发布顺序。External API 的路径、Scope、DTO、错误码、幂等和 Job 语义以主仓 [External Agent API v1 契约](https://github.com/LLMxPM/web-presentation/blob/main/docs/developer/reference/external-agent-api.md) 为准；本表中的接口信息只是实现依赖，不是第二份 API 事实源。

## 2. 背景与目标

当前 `wp` CLI 已经覆盖认证、工作空间、项目、页面、组件、资源、主题、样式、校验、截图和构建等常用流程，但与平台内容助手的通用业务能力相比，仍缺少以下能力：

- 代码规范和操作手册发现；
- 页面、组件的版本读取、源码编辑和恢复；
- 项目、页面、组件、资源、主题、样式的更新；
- 资源内容读取和可编辑内容更新；
- Mutation 任务查询与取消；
- 主题、样式复制；
- 构建产物下载；
- 能力矩阵、命令契约和 External API 版本之间的漂移检测。

本次补齐的目标不是把 CLI 改造成平台内部的 `list_entities`、`update_entity` 等模型工具，而是：

1. 让 CLI 与平台通用工具覆盖同一批核心业务语义。
2. 让所有能力只经由 External API v1 调用，保持 Backend 的权限、校验和异步任务为最终事实源。
3. 保留 CLI 面向人的资源化命令结构和面向脚本的稳定 `--json` 输出。
4. 建立 operation、Scope、幂等、异步状态和错误码的契约测试。

## 3. 设计决策

### 3.1 两种工具形态保持分层

平台内容助手使用少量通用工具，通过 `resource_type`、`action`、`view` 和操作手册分派业务动作。CLI 使用资源化命令，例如：

```text
wp page update <page_id>
wp component publish <component_id>
wp theme copy <theme_id>
```

不新增一个主入口为 `wp update_entity` 的通用命令。这样可以避免命令行失去帮助信息、参数提示和 Shell 补全能力。

### 3.2 External API v1 是 CLI 的业务边界

- CLI 不访问 Backend 数据库、Redis、Runtime、Chromium 或内部 Service。
- CLI 不复制 Backend 的 `backend/app/ai/tool_specs.py`。
- CLI 可以读取 `/api/v1/guides`、`/api/v1/standards/*`、`/api/v1/workspaces/{id}/capabilities` 和资源接口。
- CLI 只保存自身命令需要的 operation key 映射，不保存平台 AI 工具的参数 Schema、确认策略或内部工具目录。

### 3.3 共享客户端和 CLI 业务适配分层

`packages/api-client` 继续只负责：

- HTTP 方法和 `/api/v1` 公共前缀；
- PAT、Workspace Header 和 User-Agent；
- 幂等 Header；
- 错误解析；
- Mutation、Build 任务轮询；
- 二进制响应和同源安全检查。

资源语义、命令参数、终端输出和确认逻辑放在 `packages/cli`。新增业务不应把 Click 代码放进共享客户端。

### 3.4 JSON 输出保持机器可用

- `--json` 模式只输出一个完整 JSON 文档，不混入进度条和成功文案。
- 读取命令默认透传 External API 的数据结构，避免无必要的二次 DTO 漂移。
- 异步命令在 `--no-wait` 时返回受理的 Job 数据，在 `--wait` 时返回最终 Job 数据或成功结果。
- 错误输出包含稳定 `code`；PAT 不得出现在输出、异常、日志和 Job 结果中。

## 4. 能力基线

状态说明：

- 已有：当前 CLI 已有命令或共享客户端已有稳定实现。
- M1：第一批补齐，只读和发现能力。
- M2：第二批补齐，普通写入和乐观锁编辑。
- M3：第三批补齐，异步任务、恢复和交付能力。
- M4：后续增强，高风险批量能力或需要 External API 扩展的能力。
- 不纳入：当前 External API 没有对应能力，不能在 CLI 内部绕过边界实现。

| 业务能力 | 当前 CLI | 目标命令 | External API | 计划 |
|---|---|---|---|---|
| 工作空间列表 | `workspace list` | 保持 | `GET /workspaces` | 已有 |
| 工作空间详情 | 无 | `workspace get <id>` | `GET /workspaces/{id}` | M1 |
| 能力矩阵 | `workspace capabilities` | 保持并增强 JSON | `GET /workspaces/{id}/capabilities` | M1 |
| 身份详情 | `whoami` 使用工作空间列表 | 改为优先调用 `auth/whoami` | `GET /auth/whoami` | M0 |
| 操作手册 | 无 | `guide [operation_key]` | `GET /guides` | M1 |
| 页面规范 | 无 | `standards page` | `GET /standards/page` | M1 |
| 组件规范 | 无 | `standards component` | `GET /standards/component` | M1 |
| 项目读取 | `project list/get` | `project get --view` | `GET /projects/{id}` | M1 |
| 项目创建 | `project create` | 保持 | `POST /projects` | 已有 |
| 项目更新 | 无 | `project update` | `PATCH /projects/{id}` | M2 |
| 项目归档 | `project archive` | 保持 | `DELETE /projects/{id}` | 已有 |
| 页面列表和详情 | `page list/get` | 保持 | `GET /projects/{id}/pages`、`GET /pages/{id}` | 已有 |
| 页面源码读取 | `page source` | 保持并支持版本视图 | `GET /pages/{id}/source` | M1 |
| 页面版本 | 无 | `page versions/version` | `GET /pages/{id}/versions...` | M1 |
| 页面元数据更新 | 无 | `page update` | 当前没有通用 `PATCH /pages/{id}` 路由，需要先补 External API | M2-API |
| 页面源码编辑 | 无 | `page edit` | `POST /jobs/mutations/pages/edits` | M2 |
| 页面版本恢复 | 无 | `page restore` | `POST /pages/{id}/versions/{no}/restore` | M3 |
| 页面截图 | `screenshot`、`page screenshot` | 保持 | `GET /pages/{id}/screenshot` | 已有 |
| 组件列表和详情 | `component list/get` | 保持 | `GET /components...` | 已有 |
| 组件草稿读取 | `component draft` | 保持并支持版本视图 | `GET /components/{id}/draft` | M1 |
| 组件版本 | 无 | `component versions/version` | `GET /components/{id}/versions...` | M1 |
| 组件创建 | `component create` | 保持 | `POST /jobs/mutations/components` | 已有 |
| 组件源码编辑 | 无 | `component edit` | `POST /jobs/mutations/components/edits` | M2 |
| 组件元数据更新 | 无 | `component update` | 当前没有通用 `PATCH /components/{id}` 路由，需要先补 External API | M2-API |
| 组件发布 | `component publish` | 保持 | `POST /components/{id}/publish` | 已有 |
| 草稿恢复 | 无 | `component restore-draft` | `POST /components/{id}/versions/{no}/restore-draft` | M3 |
| 资源列表 | `asset list` | 增加 tags 视图 | `GET /assets` | M1 |
| 资源详情 | 无 | `asset get` | `GET /assets/{id}` | M1 |
| 资源内容 | 无 | `asset content` | `GET /assets/{id}/content` | M1 |
| 资源上传 | `asset upload` | 保持 | `POST /assets` | 已有 |
| 资源更新 | 无 | `asset update/content-update` | `PATCH /assets/{id}`、`PUT /assets/{id}/content` | M2 |
| 主题读写 | `theme list/get/create/archive` | 增加 `update/copy` | `/themes` | M2 |
| 样式读写 | `style list/get/create/archive` | 增加 `update/copy` | `/styles` | M2 |
| Mutation 任务 | 创建命令内部轮询 | `job mutation get/cancel` | `/jobs/mutations/{id}` | M3 |
| Build 任务 | `build run/status` | 增加产物下载 | `/projects/{id}/builds`、`/builds/{id}` | M3 |
| 单对象归档 | 各资源 `archive` | 保持 | 各资源 `DELETE` | 已有 |
| 批量归档 | 无 | 同类型批量归档 | `POST */batch-archive` | M4 |
| Runtime Kit | 无 | 暂不新增 | 当前无适合的 External API | 不纳入 |
| 图片生成、视觉分析 | 无 | 暂不新增 | 当前不属于 CLI External API | 不纳入 |

## 5. 分阶段实施任务

### M0：契约和基础设施整理

目标：不扩大用户可见能力，先降低后续重复代码和契约漂移风险。

任务：

- `CLI-001`：新增 CLI 能力矩阵文档和 operation key 映射说明。
- `CLI-002`：抽取统一的 Profile、Workspace、ApiClient 获取逻辑，减少命令文件重复初始化代码。
- `CLI-003`：统一 `--json` 模式，禁止等待任务时输出 Rich 进度信息污染 JSON。
- `CLI-004`：补充 Job 状态、错误码和超时配置的共享解析函数。
- `CLI-005`：将 `whoami` 改为调用 `/auth/whoami`，保留工作空间列表展示作为补充信息。
- `CLI-006`：为所有已有写命令补充幂等 Header、参数和错误码测试。
- `API-001`：对照 `external_operations.py`、实际路由和契约测试，核对 operation key 的语义、路径和请求模型。
- `API-002`：明确 `page.update`、`component.update` 是否要提供元数据更新接口；在主仓契约稳定前，CLI 不实现对应命令。

建议模块：

```text
packages/cli/src/wp/
├── command_context.py       # Profile、Workspace、ApiClient 上下文
├── command_output.py        # JSON、表格、错误和确认输出
├── operation_catalog.py     # CLI 命令与 operation key 的轻量映射
└── commands/
```

`operation_catalog.py` 不保存平台内部 AI Tool 目录，只保存 CLI 命令用于能力提示和契约校验的 operation key。

### M1：发现和只读能力

目标：让 CLI 能读取模型和人工操作所需的全部基础事实。

新增命令：

```text
wp guide
wp guide page.update
wp standards page
wp standards component
wp workspace get <workspace_id>
wp page versions <page_id>
wp page version <page_id> <version_no>
wp component versions <component_id>
wp component version <component_id> <version_no>
wp asset get <asset_id>
wp asset content <asset_id>
wp asset tags
```

实现约束：

- 大文本返回要有最大长度和截断字段。
- `asset content` 根据 Content-Type 区分文本、JSON 和二进制。
- 二进制不直接在终端打印；默认要求 `--output`。
- `guide` 展示 operation、Scope、幂等要求和描述；如果需要精确 payload Schema，必须先扩展 External API，而不是读取 Backend 内部文件。
- 版本读取必须保留版本号和对象 ID，不能把历史版本伪装成当前对象。

### M2：普通写入和源码编辑

目标：补齐平台通用 `update_entity`、源码 content 和部分 `create_entity` 能力。

新增命令：

```text
wp project update <project_id> [OPTIONS]
wp page update <page_id> [OPTIONS]
wp page edit <page_id> --file <path> --base-version <no>
wp component update <component_id> [OPTIONS]
wp component edit <component_id> --file <path> --base-draft-hash <hash>
wp asset update <asset_id> --payload-file <path>
wp asset content-update <asset_id> --file <path>
wp theme update <theme_id> --payload-file <path>
wp theme copy <theme_id> --name <name>
wp style update <style_id> --payload-file <path>
wp style copy <style_id> --name <name>
```

参数策略：

- 简单高频字段提供 Click 选项。
- configuration、route tree、palette、content 等复杂对象使用 `--payload-file`。
- `--payload-file` 只接受 UTF-8 JSON，不在错误信息中回显完整源码或 Token。
- metadata 更新和源码编辑分成不同命令，避免误把源码写入元数据接口。
- 页面和组件元数据更新必须等待主仓补齐并确认真实 External API 路由、请求 Schema、Scope 和幂等语义；不能仅依据 operation registry 的描述实现。
- 页面编辑必须携带 `base_version_no`。
- 组件编辑必须携带 `base_draft_hash`，必要时携带 `base_published_version_no`。
- 409 冲突时返回最新版本信息，提示用户重新读取后再编辑，不自动覆盖重试。

### M3：异步任务、恢复和交付

目标：把重任务从“命令内部黑盒轮询”升级为可观察、可恢复的 CLI 能力。

新增命令：

```text
wp job mutation get <job_id>
wp job mutation cancel <job_id>
wp page restore <page_id> <version_no>
wp component restore-draft <component_id> <version_no>
wp build download <job_id> --output <path>
```

任务状态约定：

```text
Mutation: queued -> running -> succeeded|failed|canceled
Build:    queued -> running -> succeeded|failed
```

任务命令要求：

- `get` 不修改任务状态。
- `cancel` 只对仍可取消状态发起请求。
- `--wait` 轮询有最大超时，不允许无限等待。
- 轮询失败时保留 Job ID，用户可以用 `job get` 继续查询。
- Job 失败原样保留 Backend 的业务错误码、message 和诊断摘要。
- 构建产物下载必须校验同源、Content-Type、文件大小和落盘路径。
- 下载采用临时文件写入，成功后原子替换目标文件。

### M4：批量和高级能力

目标：在单对象语义稳定后，再提供高风险批量操作。

候选命令：

```text
wp page archive <id> [<id> ...] --yes
wp project archive <id> [<id> ...] --yes
wp component archive <id> [<id> ...] --yes
wp asset archive <id> [<id> ...] --yes
wp theme archive <id> [<id> ...] --yes
wp style archive <id> [<id> ...] --yes
```

上线前置条件：

- Backend 明确保证同类型、同工作空间和整批原子语义。
- CLI 明确限制最多 100 个 ID，并去重。
- 默认交互确认，`--yes` 为显式绕过。
- `--json` 返回每个目标的处理结果和整批状态。
- 补充失败重试和幂等测试。

如果 External API 后续提供完整的精确操作 Schema，可再评估增加：

```text
wp operation run <operation_key> --payload-file <path>
```

该命令只能作为高级逃生舱，不能替代资源化命令，也不能直接映射平台内部 AI 工具。

## 6. 任务拆分与推荐文件边界

### 6.1 CLI 命令模块

```text
packages/cli/src/wp/commands/
├── guide.py                 # /guides
├── standards.py             # /standards/page|component
├── workspace.py             # 增加 get
├── project.py               # 增加 update
├── page.py                  # 增加 versions/version/update/edit/restore
├── component.py             # 增加 versions/version/update/edit/restore-draft
├── asset.py                 # 增加 tags/get/content/update/content-update
├── theme.py                 # 增加 update/copy
├── style.py                 # 增加 update/copy
├── job.py                   # Mutation 查询和取消
└── build.py                 # 增加 artifact download
```

单个命令文件超过职责边界或明显变长时，拆分为 `*_read.py`、`*_write.py` 或抽取 CLI gateway。不要把多个资源的业务逻辑集中到一个通用文件。

### 6.2 API Client

共享客户端只新增通用能力：

- `request` 或现有 HTTP 方法的必要增强；
- Mutation cancel 的请求封装；
- 可配置的 polling timeout 和 interval；
- 二进制下载和临时文件原子落盘辅助能力。

不把 `create_page`、`update_theme` 等业务语义塞入共享 `api-client`，避免 MCP 和 CLI 的边界混乱。

### 6.3 主仓契约

涉及以下变化时必须同步主仓：

- External API 路径、Scope、DTO、错误码变化；
- 幂等要求变化；
- Mutation Job 状态或取消语义变化；
- `/guides`、`/standards`、`/capabilities` 返回字段变化。

主仓优先补充 `tests/contracts/`，Agent Kit 再补充 MockTransport 和 CLI 适配测试。

### 6.4 已确认的主仓前置问题

实施 M2 前必须先解决以下契约问题：

1. `external_operations.py` 中的 `page.update` 描述为页面元数据更新，但当前页面路由中的同一 operation 主要用于历史版本恢复；需要拆分 operation key 或补齐元数据更新路由。
2. `external_operations.py` 中的 `component.update` 描述为组件元数据更新，但当前组件路由中的同一 operation 主要用于历史版本恢复到草稿；需要拆分 operation key 或补齐元数据更新路由。
3. 页面和组件源码编辑已有 Mutation 路径，但 CLI 需要在主仓契约中确认请求字段、版本锁字段、Job 返回结构和取消语义。
4. 构建接口目前返回产物地址，CLI 在实现 `build download` 前需要确认地址是否同源、是否为短期 Delivery URL，以及是否允许客户端携带 PAT 访问。

这四项属于 External API 契约工作，不应通过 CLI 拼接内部 Service 或猜测请求字段来规避。

## 7. 测试实施方案

### 7.1 CLI 单元测试

新增或扩展：

```text
packages/cli/tests/test_cli_commands.py
packages/cli/tests/test_guide_commands.py
packages/cli/tests/test_standard_commands.py
packages/cli/tests/test_workspace_commands.py
packages/cli/tests/test_page_commands.py
packages/cli/tests/test_component_commands.py
packages/cli/tests/test_asset_commands.py
packages/cli/tests/test_design_system_commands.py
packages/cli/tests/test_mutation_jobs.py
packages/cli/tests/test_build_commands.py
```

每个命令至少验证：

- `--help` 注册和必填参数；
- URL、HTTP 方法和 query/body；
- `Authorization`、`X-Workspace-ID` 和 `Idempotency-Key`；
- `--json` 无额外文本；
- 403、404、409、422、任务失败和超时；
- 写入失败时不会误报成功；
- 归档默认确认，取消确认不会发送请求。

### 7.2 API Client 测试

使用 `httpx.MockTransport` 验证：

- `/api/v1` 前缀只添加一次；
- GET 不发送幂等键，写操作默认发送幂等键；
- `validate` 明确不发送幂等键；
- Mutation 和 Build 轮询只在终态返回；
- 取消接口使用 POST；
- 跨源 URL 不携带 PAT；
- PNG 和 Build 产物的 Content-Type、响应头和文件大小校验。

### 7.3 契约和集成测试

主仓：

```powershell
pnpm run test:contracts
```

Agent Kit：

```powershell
uv run pytest
uv run --project packages/cli wp --help
```

真实服务验收至少覆盖：

1. 获取 Workspace 能力矩阵；
2. 创建页面 Job 并轮询到终态；
3. 用旧版本编辑页面并验证 409；
4. 创建组件、更新草稿并发布；
5. 读取和更新可编辑资源内容；
6. 触发构建、查询状态、下载产物；
7. 归档后对象不再出现在列表中。

## 8. 安全和兼容性要求

- 不在 CLI 输出 PAT、Authorization Header 或完整敏感配置。
- 不把 `--payload-file` 内容写入异常文本或 telemetry。
- 所有写入接口支持幂等重试，除非 operation 明确要求关闭幂等。
- 版本冲突不能自动覆盖。
- 归档命令必须保留确认机制。
- 二进制和构建产物使用原子文件写入。
- 旧命令和已有参数不在本次补齐中无故改名。
- 新增命令优先支持 `--json`，表格输出只作为人类可读视图。
- External API 返回未知字段时，读取命令应尽量透传到 JSON 模式，不要因字段扩展失败。

## 9. 发布顺序

### 第一批

- M0 基础整理；
- `guide`、`standards`、`workspace get`；
- 页面和组件版本只读；
- 资源详情和内容读取；
- 全部新增能力的 MockTransport 测试。

### 第二批

- 项目、主题、样式更新；
- 页面、组件元数据更新；
- 页面、组件源码编辑；
- 乐观锁冲突处理；
- 主仓 External API 契约测试。

### 第三批

- Mutation Job 查询和取消；
- 页面版本恢复、组件草稿恢复；
- 构建产物下载；
- 真实服务 E2E smoke。

### 第四批

- 批量归档；
- 可选的 `operation run` 高级命令；
- 依据真实用户使用情况再决定是否补充更多资源复制和下载能力。

## 10. 验收标准

本项目完成的判断标准：

1. 能力矩阵中的每个“已支持” operation 都有 CLI 命令、API 路径、Scope 和测试。
2. M1 只读能力全部可通过 `--json` 稳定输出。
3. M2 写入能力全部携带正确幂等语义，并能处理 409 和 422。
4. 页面、组件重任务可以受理、查询、等待、失败透传和取消。
5. CLI 不直接依赖 Backend 内部 AI 工具目录或内部服务。
6. `uv run pytest`、主仓契约测试和目标真实服务 smoke 全部通过。
7. README、CLI 帮助、命令示例和 External API 版本说明同步更新。

## 11. 风险与处理

| 风险 | 处理方式 |
|---|---|
| External API 的字段或错误码漂移 | 主仓契约测试先行，Agent Kit 使用 MockTransport 固化适配行为 |
| 复杂 payload 参数过多 | 高频字段使用选项，复杂对象使用 `--payload-file` |
| CLI 与平台通用工具出现第二套规则 | 只对齐 External API 语义，不复制内部 `tool_specs.py` |
| 源码编辑覆盖用户最新版本 | 强制版本号/hash，409 后重新读取，不自动覆盖 |
| 等待任务阻塞终端 | 默认有超时，支持 `--no-wait` 和独立 Job 查询 |
| 批量归档误操作 | 延后到 M4，限制同类型、最多 100 项并强制确认 |
| 构建产物 URL 泄露 PAT | 只允许同源请求，下载时执行 Content-Type 和大小校验 |
