"""文件功能：提供统一的异步 Mutation Job 查询、等待、取消与重试命令。"""

from __future__ import annotations

import click

from wp.client import ApiClientError
from wp.commands.common import (
    get_client,
    handle_api_error,
    idempotency_key_option,
    output_result,
    require_success_job,
)
from wp.openapi_help import contract, openapi_command


@click.group("job")
def job_group() -> None:
    """异步任务管理。"""


@openapi_command(job_group, "get", contract("GET", "/api/v1/jobs/mutations/{job_id}"))
@click.argument("job_id")
@click.pass_context
def get_job_cmd(ctx: click.Context, job_id: str) -> None:
    """查询 Mutation Job。"""

    try:
        output_result(ctx, get_client(ctx).get_mutation_job(job_id))
    except ApiClientError as err:
        handle_api_error("查询 Job 失败", err)


@openapi_command(
    job_group,
    "wait",
    contract("GET", "/api/v1/jobs/mutations/{job_id}"),
    examples=("wp --json job wait <job_id> --timeout 120",),
)
@click.argument("job_id")
@click.option("--timeout", default=120.0, type=float, show_default=True, help="等待终态的最长秒数")
@click.pass_context
def wait_job_cmd(ctx: click.Context, job_id: str, timeout: float) -> None:
    """等待 Mutation Job 进入终态。"""

    try:
        result = get_client(ctx).poll_mutation_job(job_id, timeout_seconds=timeout)
        require_success_job(result, ctx=ctx)
        output_result(ctx, result)
    except ApiClientError as err:
        handle_api_error("等待 Job 失败", err)


@openapi_command(job_group, "cancel", contract("POST", "/api/v1/jobs/mutations/{job_id}/cancel"))
@click.argument("job_id")
@idempotency_key_option
@click.pass_context
def cancel_job_cmd(ctx: click.Context, job_id: str) -> None:
    """取消 pending 或 running Mutation Job。"""

    try:
        output_result(
            ctx,
            get_client(ctx).cancel_mutation_job(
                job_id,
                idempotency_key=ctx.obj.get("idempotency_key"),
            ),
        )
    except ApiClientError as err:
        handle_api_error("取消 Job 失败", err)


@openapi_command(job_group, "retry", contract("POST", "/api/v1/jobs/mutations/{job_id}/retry"))
@click.argument("job_id")
@idempotency_key_option
@click.pass_context
def retry_job_cmd(ctx: click.Context, job_id: str) -> None:
    """重试一个明确允许人工重试的失败 Job。"""

    try:
        output_result(
            ctx,
            get_client(ctx).retry_mutation_job(
                job_id,
                idempotency_key=ctx.obj.get("idempotency_key"),
            ),
        )
    except ApiClientError as err:
        handle_api_error("重试 Job 失败", err)
