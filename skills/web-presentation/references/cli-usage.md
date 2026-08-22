# `wp` CLI 调用参考

本参考只记录 Agent 调用 CLI 的稳定方式和工作流检查点。具体参数以当前安装版本的 `wp --help`、子命令帮助和平台 `/api/v1/guides` 返回为准；如果帮助与本文不一致，以运行结果为准。

## 运行 CLI

在已安装 `wp` 的环境中直接调用：

```bash
wp --help
wp page --help
```

在 `web-presentation-agent-kit` 仓库开发或未安装入口时调用：

```bash
uv run --project packages/cli wp --help
uv run --project packages/cli wp page --help
```

安装为可执行命令：

```bash
uv tool install --editable packages/cli
wp --help
```

不要反复启动平台服务；CLI 只连接已有服务。Endpoint 配置填写平台服务根地址，例如 `http://127.0.0.1:8000` 或 `https://api.example.com`，不要包含 `/api/v1`。

## 登录、Profile 和工作空间

推荐让 CLI 交互式隐藏输入 PAT，不要把真实 PAT 写入命令、聊天、日志或脚本：

```bash
wp login
wp login --endpoint https://api.example.com
wp whoami
wp doctor
```

如果使用非默认环境，先切换 Profile。Profile 保存 Endpoint、PAT 和默认工作空间：

```bash
wp profile list
wp profile use production
```

写入前必须确定唯一工作空间：

```bash
wp workspace list
wp workspace use <workspace_id>
wp workspace capabilities --workspace-id <workspace_id>
```

单次命令也可以用全局选项覆盖本地默认值：

```bash
wp --profile production --workspace <workspace_id> project list
```

`--workspace` 不能替代平台的权限校验；它只是本次请求的工作空间上下文。没有明确空间时不执行写入。

## 输出和发现

自动化或需要稳定解析时，把 `--json` 放在子命令之前：

```bash
wp --json workspace list
wp --json page get <page_id>
wp --json job mutation get <job_id> --wait
```

需要确定复杂操作的请求字段、前置条件、幂等要求或错误恢复时，查询平台发布的操作手册：

```bash
wp guide
wp guide page.create
wp guide page.update
```

页面或组件源码任务前先遵守 Skill 中的内容、构图和 Runtime Kit 约束，再使用 CLI 做独立源码预检：

```bash
wp --json validate ./Page.vue --type page
wp --json validate ./MetricCard.vue --type component
```

`validate` 是诊断，不是写入；它通过后仍需遵守目标接口的版本、草稿和异步任务约束。

## 常用只读命令

```bash
# 项目和页面
wp project list
wp project get <project_id>
wp page list --project-id <project_id>
wp page get <page_id>
wp page source <page_id>

# 组件、资源、主题和样式
wp component list
wp component get <component_id>
wp component draft <component_id>
wp asset list
wp theme list
wp theme get <theme_id>
wp style list
wp style get <style_id>

# 页面截图；默认写入 page-<page_id>-v<version>.png
wp screenshot <page_id> --output .tmp/page.png
wp page screenshot <page_id> --output .tmp/page.png
```

截图命令通过一次 External API GET 获取最新 PNG，返回实际页面版本和文件路径，不要为截图命令额外创建或轮询 Mutation Job。截图用于视觉确认时，检查画布尺寸、溢出、文字可读性、主体视觉重心、资源加载和空态/加载态/错误态。

## 写入命令和异步任务

先读目标对象和操作手册，再执行最小范围写入。当前 CLI 常用写入形态如下：

```bash
# 轻量业务对象
wp project create --name "季度汇报" --description "2026 Q3"
wp page update <page_id> --title "新标题" --idempotency-key <key>
wp component update <component_id> --name "指标卡" --summary "展示核心指标" --idempotency-key <key>

# 页面/组件源码创建：完整 Vue SFC 放在本地文件中
wp page create --project-id <project_id> --name "概览" --file ./Page.vue
wp component create --name "指标卡" --import-name MetricCard --file ./MetricCard.vue
```

页面和组件源码创建、编辑等重任务可能由平台异步处理。创建命令默认等待；需要先拿到任务 ID 时使用 `--no-wait`，然后轮询：

```bash
wp page create --project-id <project_id> --name "概览" --file ./Page.vue --no-wait
wp job mutation get <job_id> --wait --timeout 60
```

只接受平台返回的 `pending | running | succeeded | failed | canceled` 终态语义。`succeeded` 后再读取最新对象或截图；`failed` 时保留 `code`、错误消息和诊断摘要。只有平台明确该任务可人工重试时才执行：

```bash
wp job mutation retry <job_id> --idempotency-key <retry-key>
```

版本、草稿 hash、权限或参数冲突不能靠原命令盲重试；先重新读取当前对象和指南。

## 归档和凭证边界

CLI 的 `archive` 命令是可审计的归档语义，不是永久删除：

```bash
wp page archive <page_id>
wp component archive <component_id>
wp asset archive <asset_id>
```

默认保留交互确认。只有用户已经明确授权当前归档动作时，才可以追加 `--yes`；不要把 `--yes` 当作 Agent 的默认参数。CLI 不提供永久删除、跨工作空间写入、直接数据库/Runtime/Chromium 访问或 Build 产物下载。

## 命令选择速查

| 用户目标 | 先做什么 | CLI 入口 |
| --- | --- | --- |
| 确认身份和连通性 | 检查 Profile、PAT、空间 | `wp doctor`、`wp whoami` |
| 选择工作空间 | 列出并验证空间 | `wp workspace list`、`wp workspace use <id>` |
| 了解可用操作 | 查索引，再查精确 Schema | `wp guide`、`wp guide <operation_key>` |
| 读页面源码 | 先读元数据，再读源码 | `wp page get <id>`、`wp page source <id>` |
| 预检本地源码 | 指定实体类型 | `wp validate <file> --type page\|component` |
| 创建页面/组件 | 先读 Skill 约束、项目基线和操作手册 | `wp page create ...`、`wp component create ...` |
| 等待重任务 | 查询并保留 Job 结果 | `wp job mutation get <id> --wait` |
| 视觉确认 | 获取最新版本截图 | `wp screenshot <page_id> -o <file>` |
| 轻量元数据更新 | 提供幂等键 | `wp page update ...`、`wp component update ...` |
| 归档 | 保留确认 | `wp <resource> archive <id>` |

Build External API 和产物下载契约尚未冻结，当前不要通过 CLI 猜测或拼接构建命令。
