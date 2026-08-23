# Web Presentation API Client

`wp_api_client` 是 `web-presentation` External API v1 的共享 Python 客户端源码，供 `web-presentation-cli` 使用。

它在仓库中保持独立的模块边界，但会被打包进 CLI 的发行物。普通用户不需要单独安装这个 workspace 包，直接安装 CLI 即可：

```bash
uv tool install web-presentation-cli
# 或
pipx install web-presentation-cli
```

仓库地址：[web-presentation-agent-kit](https://github.com/LLMxPM/web-presentation-agent-kit)。
