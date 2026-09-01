# CLI External API v1 能力矩阵

当前 CLI 按首版本地开发契约实现，不提供旧命令、旧参数或兼容层。Backend External API 是权限、Schema、错误码和任务状态的唯一事实源。

## 命令矩阵

| 资源 | CLI 命令 |
| --- | --- |
| 系统 | `wp system version`, `wp system health` |
| 标准 | `wp standards page`, `wp standards component` |
| 动态请求契约 | 目标叶子命令的 `--help` 从 Backend OpenAPI 展示 |
| Runtime Kit | `wp runtime-kit list`, `wp runtime-kit get <item>` |
| 字体 | `wp font list` |
| 项目 | `list`, `get`, `create`, `update`, `archive`, `configuration get/update`, `route get/replace`, `apply-style`, `build-assets update` |
| 页面 | `list`, `get`, `create`, `copy`, `update`, `source`, `edit`, `version list/get`, `dependencies`, `validate`, `screenshot`, `archive` |
| 组件 | `list`, `get`, `create`, `update`, `edit`, `version list/get`, `dependencies`, `validate`, `publish`, `archive` |
| 资源 | `list`, `get`, `create`, `upload`, `update`, `copy`, `content get/update/preview`, `tags list`, `archive` |
| 主题 | `list`, `get`, `create`, `update`, `copy`, `archive` |
| 样式 | `list`, `get`, `create`, `update`, `copy`, `archive` |
| Mutation Job | `wp job get`, `wait`, `cancel`, `retry` |

## 文件参数

复杂参数不通过长命令行字符串拼接：

- `--payload-file`：完整 JSON 请求对象。
- `--edits-file`：源码结构化编辑数组。
- `--preview-schema-file`：Preview Schema JSON 对象。
- `--route-file`：完整项目路由树 JSON 对象。
- `--content-file`：UTF-8 原始文本内容。
- `--ids-file`：批量归档用的正整数数组。

示例：

```bash
wp --workspace 1 project configuration update 10 --payload-file configuration.json
wp page edit 20 --base-version-no 3 --edits-file edits.json
wp asset content preview 30 --content-file diagram.svg
wp component update 40 --payload-file component-metadata.json
wp page archive --ids-file page-ids.json --yes
```

页面和组件创建、源码编辑、组件复杂元数据更新默认等待 Mutation Job 终态；使用 `--no-wait` 只返回 Job，再使用 `wp job wait <job_id>` 轮询。

## 明确不支持

当前 CLI 不提供：

- Agent Session/Run/HITL 和动态工具披露；
- 图片生成与图片识别；
- Build 任务、构建状态和产物下载；
- 永久删除和 Restore；
- MCP Server。

校验、工作空间隔离、PAT、Scope、幂等键和乐观锁均由主仓 External API 最终执行。
