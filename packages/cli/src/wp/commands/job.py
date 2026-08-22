"""文件功能：提供统一的异步 Mutation Job 查询、等待、取消与重试命令。"""

from __future__ import annotations

import click

from wp.client import ApiClientError
from wp.commands.common import get_client, handle_api_error, output_result


@click.group("job")
def job_group() -> None:
    """异步任务管理。"""


@job_group.command("get")
@click.argument("job_id")
@click.pass_context
def get_job_cmd(ctx: click.Context, job_id: str) -> None:
    """查询 Mutation Job。"""

    try:
        output_result(ctx, get_client(ctx).get_mutation_job(job_id))
    except ApiClientError as err:
        handle_api_error("查询 Job 失败", err)


@job_group.command("wait")
@click.argument("job_id")
@click.option("--timeout", default=120.0, type=float, show_default=True)
@click.pass_context
def wait_job_cmd(ctx: click.Context, job_id: str, timeout: float) -> None:
    """等待 Mutation Job 进入终态。"""

    try:
        output_result(ctx, get_client(ctx).poll_mutation_job(job_id, timeout_seconds=timeout))
    except ApiClientError as err:
        handle_api_error("等待 Job 失败", err)


@job_group.command("cancel")
@click.argument("job_id")
@click.option("--idempotency-key")
@click.pass_context
def cancel_job_cmd(ctx: click.Context, job_id: str, idempotency_key: str | None) -> None:
    """取消 pending 或 running Mutation Job。"""

    try:
        output_result(ctx, get_client(ctx).cancel_mutation_job(job_id, idempotency_key=idempotency_key))
    except ApiClientError as err:
        handle_api_error("取消 Job 失败", err)


@job_group.command("retry")
@click.argument("job_id")
@click.option("--idempotency-key")
@click.pass_context
def retry_job_cmd(ctx: click.Context, job_id: str, idempotency_key: str | None) -> None:
    """重试一个明确允许人工重试的失败 Job。"""

    try:
        output_result(ctx, get_client(ctx).retry_mutation_job(job_id, idempotency_key=idempotency_key))
    except ApiClientError as err:
        handle_api_error("重试 Job 失败", err)
