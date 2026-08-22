# CLI External API v1 能力矩阵

CLI 以 Backend `/api/v1/guides` 为契约事实源，不复制内部 AI 工具 Schema。

| 能力 | CLI | External API |
| --- | --- | --- |
| Guides 索引/详情 | `wp guide [operation_key]` | `GET /guides[/{operation_key}]` |
| 页面安全元数据 | `wp page update` | `PATCH /pages/{id}` |
| 组件安全元数据 | `wp component update` | `PATCH /components/{id}` |
| Mutation 查询 | `wp job mutation get` | `GET /jobs/mutations/{id}` |
| Mutation 取消 | `wp job mutation cancel` | `POST /jobs/mutations/{id}/cancel` |
| Mutation 人工重试 | `wp job mutation retry` | `POST /jobs/mutations/{id}/retry` |

所有逻辑写操作允许传入 `--idempotency-key`；自动生成时客户端在 `_client.idempotency_key` 中回显。轮询只识别 `pending | running | succeeded | failed | canceled`。

Build 与产物下载契约尚未冻结，因此不属于 agent-kit 支持范围，后续需在主仓冻结持久化 Worker、取消协议和 PAT 交付语义后另行设计。
