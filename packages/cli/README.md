# Web Presentation CLI (`wp`)

面向 `web-presentation` AI 演示文稿创作平台的官方命令行与 Agent 工具包。

External API 路径、Scope、错误码、幂等和异步任务语义以主仓 [External Agent API v1 契约](https://github.com/LLMxPM/web-presentation/blob/main/docs/developer/reference/external-agent-api.md) 为准；CLI 命令和参数以本仓 `wp --help` 与 CLI 实施文档为准。

## 安装与快速开始

```bash
# 在 agent-kit 仓库根目录安装 CLI
uv pip install -e ./packages/cli

# 登录并绑定 PAT 令牌
wp login --token wp_pat_xxxxxxxx.yyyyyyyyyyyyyyyy
# 生产环境可指定 Backend 根地址（不要包含 /api/v1）
wp login --endpoint https://api.example.com --token wp_pat_xxxxxxxx.yyyyyyyyyyyyyyyy

# 检查环境与连通性
wp doctor

# 查看授权的工作空间并切换当前工作空间
wp workspace list
wp workspace use <workspace_id>

# 查看并切换默认 Profile（Profile 保存 Backend 地址、PAT 和默认工作空间）
wp profile list
wp profile use production

# 常用操作
wp project list
wp page list --project-id <project_id>
wp component list
wp asset list
wp theme list
wp style list
wp validate <page_or_component.vue>
wp guide page.update
wp page update <page_id> --title "新标题"
wp job mutation get <job_id> --wait
```

Build External API 尚未冻结，CLI 不提供构建和产物下载命令。
