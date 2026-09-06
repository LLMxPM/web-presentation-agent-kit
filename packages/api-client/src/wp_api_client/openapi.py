"""文件功能：严格获取公开 OpenAPI，并提供不包含凭证的分阶段错误信息。"""

from urllib.parse import urlsplit, urlunsplit

import httpx

from wp_api_client.client import ApiClientError


def safe_url(value: str) -> str:
    """保留定位所需地址与路径，移除用户信息、查询参数和片段。"""
    parts = urlsplit(value)
    return urlunsplit((parts.scheme, parts.netloc.rsplit('@', 1)[-1], parts.path, '', ''))


def fetch_openapi(client: httpx.Client, *, timeout_seconds: float, user_agent: str, metadata: dict | None = None) -> dict:
    """无凭证获取契约；不重试、不跟随重定向，失败保留阶段与响应元数据。"""
    details = metadata if metadata is not None else {}
    details.update({'url': safe_url(str(client.base_url.join('openapi.json'))),
               'status_code': None, 'content_type': None, 'request_id': None, 'stage': 'request'})

    def fail(code: str, message: str) -> None:
        """统一抛出结构化错误，不包含响应正文或底层可能含凭证的异常文本。"""
        raise ApiClientError(message, code=code, details=dict(details),
                             status_code=details['status_code'] or 503,
                             request_id=details['request_id'])

    try:
        response = client.get('/openapi.json', timeout=timeout_seconds, follow_redirects=False,
                              headers={'Accept': 'application/json', 'User-Agent': user_agent})
    except httpx.TimeoutException:
        fail('OPENAPI_TIMEOUT', '读取 OpenAPI 超时。')
    except httpx.RequestError:
        fail('OPENAPI_UNAVAILABLE', '无法连接 OpenAPI，请检查地址、网络与 TLS。')
    details.update(url=safe_url(str(response.request.url)), status_code=response.status_code,
                   content_type=response.headers.get('content-type'),
                   request_id=response.headers.get('x-request-id'), stage='http')
    if not response.is_success:
        fail('OPENAPI_HTTP_ERROR', f'读取 OpenAPI 失败：HTTP {response.status_code}。')
    details['stage'] = 'content_type'
    media_type = (details['content_type'] or '').split(';')[0].strip().lower()
    if media_type != 'application/json' and not (media_type.startswith('application/') and media_type.endswith('+json')):
        hint = ' 请检查网关是否返回了前端入口或其它 HTML 页面。' if media_type == 'text/html' else ''
        fail('OPENAPI_CONTENT_TYPE_INVALID', 'OpenAPI 响应 Content-Type 不是 JSON。' + hint)
    details['stage'] = 'json'
    try:
        payload = response.json()
    except ValueError:
        fail('OPENAPI_INVALID', 'OpenAPI 响应不是合法 JSON。')
    details['stage'] = 'document'
    if not isinstance(payload, dict) or not isinstance(payload.get('paths'), dict) or not str(payload.get('openapi', '')).startswith('3.'):
        fail('OPENAPI_INVALID', 'OpenAPI 根结构无效：需要 OpenAPI 3.x 与 paths 对象。')
    return payload
