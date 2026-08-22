"""文件功能：提供 Mutation Job 查询、取消与人工重试命令。"""

from __future__ import annotations

import click

from wp.client import ApiClient, ApiClientError
from wp.config import get_profile, load_config
from wp.formatter import print_error, print_json


@click.group("job")
def job_group() -> None:
    """异步任务管理。"""


@job_group.group("mutation")
def mutation_group() -> None:
    """Mutation Job 管理。"""


def _client(ctx: click.Context) -> ApiClient:
    """按当前 CLI 上下文创建共享 API Client。"""

    profile = get_profile(load_config(), ctx.obj.get("profile"))
    return ApiClient(profile, workspace_id=ctx.obj.get("workspace_id"))


@mutation_group.command("get")
@click.argument("job_id")
@click.option("--wait", is_flag=True, help="持续轮询直到任务终态")
@click.option("--timeout", default=60.0, show_default=True, type=float, help="等待超时秒数")
@click.pass_context
def get_mutation_job_cmd(ctx: click.Context, job_id: str, wait: bool, timeout: float) -> None:
    """查询 Mutation Job；可选择等待 pending/running 收敛。"""

    try:
        client = _client(ctx)
        result = client.poll_mutation_job(job_id, timeout_seconds=timeout) if wait else client.get_mutation_job(job_id)
        print_json(result)
    except ApiClientError as err:
        print_error(f"查询 Mutation Job 失败: {err.message}", code=err.code, details=err.details)
        raise SystemExit(1)


@mutation_group.command("cancel")
@click.argument("job_id")
@click.option("--idempotency-key", help="复用已有幂等键以安全重放同一取消请求")
@click.pass_context
def cancel_mutation_job_cmd(ctx: click.Context, job_id: str, idempotency_key: str | None) -> None:
    """请求取消 pending 或 running Mutation Job。"""

    try:
        print_json(_client(ctx).cancel_mutation_job(job_id, idempotency_key=idempotency_key))
    except ApiClientError as err:
        print_error(f"取消 Mutation Job 失败: {err.message}", code=err.code, details=err.details)
        raise SystemExit(1)


@mutation_group.command("retry")
@click.argument("job_id")
@click.option("--idempotency-key", help="复用已有幂等键以安全重放同一人工重试请求")
@click.pass_context
def retry_mutation_job_cmd(ctx: click.Context, job_id: str, idempotency_key: str | None) -> None:
    """为 retryable failed Job 创建一个保留原乐观锁基线的新任务。"""

    try:
        print_json(_client(ctx).retry_mutation_job(job_id, idempotency_key=idempotency_key))
    except ApiClientError as err:
        print_error(f"重试 Mutation Job 失败: {err.message}", code=err.code, details=err.details)
        raise SystemExit(1)
