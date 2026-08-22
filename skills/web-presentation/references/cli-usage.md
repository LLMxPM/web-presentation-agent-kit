# CLI 工作流

本参考只说明外部 Agent 如何用 `wp` 发现能力和执行工作流。参数、请求 Schema、Scope、错误码和响应字段以当前安装版本的 `wp --help`、`wp <group> --help`、`wp guide` 以及 Backend External API v1 契约为准。

## 入口与认证

Endpoint 填 Backend 根地址，不要包含 `/api/v1`。优先交互式输入 PAT，不要把真实 Token 放进命令、Skill、日志、源码或回复：

```bash
wp --help
wp login
wp whoami
wp doctor
wp profile list
wp profile use <profile>
```

未安装入口或在 agent-kit 仓库开发时使用：

```bash
uv run --project packages/cli wp --help
```

每次写入前确认工作空间；可以设置默认空间，也可以对单次命令覆盖：

```bash
wp workspace list
wp workspace use <workspace_id>
wp --json --workspace <workspace_id> workspace capabilities
wp --json --workspace <workspace_id> project list
```

`--workspace` 只是请求上下文，不替代 Backend 的权限和归属校验。没有明确唯一空间时不写入。

## 输出、规范与操作指南

全局选项必须放在子命令之前：

```bash
wp --json page get <page_id>
wp --json job wait <job_id>
```

`--json` 让支持表格或代码视图的命令输出结构化 JSON；创建、更新、校验、能力目录和 Job 等复杂响应默认就是 JSON。

源码任务先读取当前公开规范：

```bash
wp standards page
wp standards component
```

首次使用复杂操作、不确定 payload/edits/options 或遇到参数错误时读取操作指南：

```bash
wp guide list
wp guide get <operation_key>
wp page --help
wp page edit --help
```

命令的具体参数以当前 CLI 帮助和操作指南为准，不要凭记忆拼接请求字段。

## 读取顺序

先读元数据，再读需要的视图：

```bash
wp --json project list
wp --json project get <project_id>
wp --json project configuration get <project_id>
wp --json project route get <project_id>
wp --json page list --project-id <project_id>
wp --json page get <page_id>
wp --json page source <page_id>
wp --json page dependencies <page_id>
```

跨页面复用前查询工作空间资产和组件，不能仅凭名称猜测：

```bash
wp --json component list
wp --json component list --scope suggested --project-id <project_id>
wp --json component dependencies <component_id>
wp --json asset list
wp --json asset get <asset_id>
wp --json theme list
wp --json style list
wp --json font list
wp --json runtime-kit list
wp --json runtime-kit get <item>
```

## 写入命令选择

复杂 JSON 使用文件，不把长 JSON 拼在命令行中：

| 目标 | CLI 入口 | 关键基线 |
| --- | --- | --- |
| 项目名称/说明 | `wp project update` | 最新项目 ID |
| 项目展示配置 | `wp project configuration update` | 最新 configuration |
| 项目路由树 | `wp project route replace` | 最新完整 route tree；全量替换 |
| 页面元数据 | `wp page update` | 最新页面 ID |
| 页面新建 | `wp page create --project-id ... --file ...` | 项目 ID、完整 SFC |
| 页面源码编辑 | `wp page edit <page_id>` | `current_version_no`、最新源码片段 |
| 组件新建 | `wp component create` | 类型、完整 SFC、preview schema |
| 组件源码编辑 | `wp component edit <component_id>` | `base_version_no`、`base_draft_hash`、最新源码 |
| 组件元数据/schema | `wp component update` | 最新 draft/version 基线 |
| 主题/样式/资源 | 对应 `create/update/copy/upload` | 最新对象、真实字段和幂等键 |

文件参数按命令帮助为准，常见的是 `--payload-file`、`--edits-file`、`--preview-schema-file`、`--content-file`、`--route-file` 和 `--ids-file`。页面或组件的 `--edits-file` 必须使用约定的结构化编辑数组，字段和允许的 `type` 见[校验与交付](./validation-and-delivery.md#editsjson-格式)。

所有会改变数据、取消任务或人工重试任务的命令使用 `--idempotency-key`。网络超时后只有在确认请求没有产生可见结果时，才用同一个业务 key 重放；不同业务请求不得复用 key。

## 异步任务

页面/组件创建和源码编辑等重任务默认等待；使用 `--no-wait` 时保存返回的 Job ID：

```bash
wp page create --project-id <project_id> --name "核心结论" --file ./Page.vue --no-wait
wp job wait <job_id> --timeout 120
wp job get <job_id>
```

只接受 `pending | running | succeeded | failed | canceled`。`succeeded` 后重新读对象；`failed` 或 `canceled` 不得当作成功。仅当平台明确任务可人工重试时才使用：

```bash
wp job retry <job_id> --idempotency-key <new-retry-key>
```

版本冲突、权限错误、参数错误和资源缺失先重新读取/修正，不执行原命令盲重试。

## 校验、截图与归档

候选源码需要独立预检时使用：

```bash
wp --json page validate <page_id> --mode content --source-file ./Page.vue
wp --json component validate <component_id> --mode content --source-file ./MetricCard.vue
```

写入任务本身会执行平台编译、渲染和布局校验；独立 `validate` 是候选预检或失败诊断，不是绕过写入流程的替代品。视觉确认获取最新截图：

```bash
wp page screenshot <page_id> --output .tmp/page.png
```

归档不等于删除，`--yes` 只在用户已明确授权当前归档动作时使用：

```bash
wp page archive <page_id>
wp component archive <component_id>
wp asset archive <asset_id>
```
