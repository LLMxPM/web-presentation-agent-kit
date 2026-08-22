# MCP External API v1 实施说明

MCP Server 通过共享 API Client 调用 Backend，不访问数据库、Redis、Runtime 或内部 Service。

当前公开工具包括 Guides 索引/详情、开发规范、工作空间与项目查询、页面/组件安全元数据更新，以及 Mutation Job 查询、取消和人工重试。`wp_get_operation_guide(operation_key?)` 是复杂请求 Schema 的发现入口；`wp_update_entity` 仅允许页面的 `title/summary/speaker_notes` 和组件的 `name/summary`。

取消和重试接受已有幂等键；自动生成的键、request ID 和服务端重试提示会保留在结构化结果或错误中。Mutation 轮询状态固定为 `pending | running | succeeded | failed | canceled`。

Build External API 与产物交付契约尚未冻结，MCP 不注册构建或下载工具。
