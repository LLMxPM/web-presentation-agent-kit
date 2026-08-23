# CLI 公开分发

本仓库通过 PyPI 分发一个包：`web-presentation-cli`。用户安装这个包后即可获得 `wp` 命令；共享 API Client 会作为内部模块一起打进 wheel 和 source distribution，不需要单独安装。

GitHub Actions 已配置为：推送 `v*` 版本标签后，先运行 CLI/API Client 测试，再构建并发布一个 CLI 发行包。工作流文件为 `.github/workflows/publish.yml`。

## 首次配置

### 1. 创建 PyPI Trusted Publisher

登录 [PyPI](https://pypi.org/)，为 `web-presentation-cli` 添加 Pending Publisher：

| 字段 | 值 |
| --- | --- |
| Owner | `LLMxPM` |
| Repository name | `web-presentation-agent-kit` |
| Workflow name | `publish.yml` |
| Environment name | `pypi` |

首次发布前项目尚不存在时，使用 PyPI 的 Pending Publisher；首次成功发布后，它会绑定为正式 Trusted Publisher。

### 2. 创建 GitHub Environment

在仓库的 **Settings → Environments** 创建名为 `pypi` 的 Environment。可以为它配置 Required reviewers，让每次生产发布都需要人工批准；不需要添加 Secret，也不要把 PyPI Token 写入仓库。

## 发布一个版本

发布前只需要在 `packages/cli/pyproject.toml` 中更新 CLI 版本号，然后执行：

```bash
uv lock
uv run pytest packages/api-client/tests packages/cli/tests
git add packages/cli/pyproject.toml uv.lock
git commit -m "发布 CLI v0.1.0"
git push origin master

git tag -a v0.1.0 -m "v0.1.0"
git push origin v0.1.0
```

标签版本必须与 `packages/cli/pyproject.toml` 的 `project.version` 完全一致。推送标签后，在 GitHub **Actions → Publish Python packages** 查看构建和发布状态。

## 用户安装

```bash
uv tool install web-presentation-cli
# 或
pipx install web-presentation-cli
```

安装完成后即可使用：

```bash
wp --help
```

## 本地构建检查

正式发布前可以只构建 CLI 而不上传：

```bash
uv build --package web-presentation-cli --out-dir dist
```

如果需要人工上传，使用 PyPI Token 设置 `UV_PUBLISH_TOKEN` 后执行 `uv publish`；优先使用 GitHub Actions 的 Trusted Publishing，避免长期 Token 泄露和维护成本。
