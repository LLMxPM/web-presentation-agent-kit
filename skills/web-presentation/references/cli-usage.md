# CLI 工作流

本参考只说明 `wp` 的本地上下文、文件输入和任务控制。命令参数和 payload Schema 以目标叶子命令的当前 `--help` 为准，不在 Skill 中复制。

## Profile 与工作空间

Endpoint 填 Backend 根地址，不包含 `/api/v1`。优先让 `wp login` 交互式读取 PAT，不把 Token 写进命令、文件、日志或回复：

```bash
wp login
wp whoami
wp doctor
wp profile list
wp profile use <profile>
wp workspace list
wp workspace use <workspace_id>
```

全局选项必须放在子命令之前：

```bash
wp --profile production --workspace <workspace_id> --json project list
```

`--workspace` 只设置请求上下文，不替代 Backend 权限和对象归属校验。没有明确唯一工作空间时不写入。

## Help 与输出

复杂命令先读取完整叶子帮助：

```bash
wp page create --help
wp component update --help
```

帮助始终包含本地调用语法；Backend 可达时还会从 `/openapi.json` 展示当前请求参数、content type、请求体和递归引用 Schema。出现“当前 Backend Schema 未加载”时只表示动态 Schema 不可用；需要提交请求时先恢复 Backend 连通性再读取帮助。

`--json` 用于稳定解析表格型输出，复杂响应默认已经是 JSON。不要解析 Rich 表格文案来获取 ID、版本或状态。

## 文件参数

复杂 JSON、Vue SFC 和资源内容通过文件传入，不在 Shell 中拼接长文本。常见入口包括：

- `--payload-file`：完整 JSON 请求体；
- `--edits-file`：结构化编辑 JSON 数组；
- `--preview-schema-file`：组件预览 Schema JSON 对象；
- `--content-file`：完整 UTF-8 文本；
- `--route-file`：完整路由树 JSON；
- `--ids-file`：只含正整数的 JSON 数组。

具体根节点、字段、枚举和参数组合只以对应命令 `--help` 中的当前 OpenAPI Schema 为准。

## 写入、幂等与任务

所有写入、取消和人工重试命令都使用业务级 `--idempotency-key`。网络超时后，只有重放同一业务请求时复用原 key；不同请求不得复用。

页面/组件重任务默认等待。使用 `--no-wait` 时保存返回的 Job ID，再查询或等待：

```bash
wp --json job get <job_id>
wp --json job wait <job_id> --timeout 120
```

`pending`、`running` 不是完成；只有 `succeeded` 表示成功。`failed` 或 `canceled` 必须按错误码、版本基线和诊断处理。仅当平台明确标记任务可人工重试时使用 `wp job retry`。

归档默认保留交互确认。只有用户已明确授权当前归档目标时才使用 `--yes`；批量目标先核对 `--ids-file` 中的完整 ID 集合。
