"""文件功能：验证契约传输错误分类及敏感信息边界。"""

import httpx
import pytest

from wp_api_client.client import ApiClient, ApiClientError


@pytest.mark.parametrize('status,headers,body,code', [
    (200, {'content-type': 'text/html'}, '<html>secret</html>', 'OPENAPI_CONTENT_TYPE_INVALID'),
    (200, {}, '{}', 'OPENAPI_CONTENT_TYPE_INVALID'),
    (200, {'content-type': 'application/json'}, 'invalid', 'OPENAPI_INVALID'),
    (200, {'content-type': 'application/json'}, '{}', 'OPENAPI_INVALID'),
    (302, {'location': '/login'}, '', 'OPENAPI_HTTP_ERROR'),
    (404, {}, '', 'OPENAPI_HTTP_ERROR'),
    (500, {}, '', 'OPENAPI_HTTP_ERROR'),
])
def test_response_errors(status, headers, body, code):
    """错误只输出安全元数据，不泄露正文或 URL 凭证。"""
    api = ApiClient('https://user:password@backend.test', token='pat_secret')
    api.client.close()
    api.client = httpx.Client(base_url=api.endpoint, transport=httpx.MockTransport(
        lambda request: httpx.Response(status, headers={**headers, 'x-request-id': 'req-1'}, text=body)))
    try:
        with pytest.raises(ApiClientError) as caught:
            api.get_openapi_schema()
        error = caught.value
        assert error.code == code
        assert error.details['status_code'] == status
        assert error.details['request_id'] == 'req-1'
        assert not any(secret in str(error.details) + error.message for secret in ('password', 'pat_secret', '<html>'))
    finally:
        api.close()


@pytest.mark.parametrize('exception,code', [(httpx.ConnectError, 'OPENAPI_UNAVAILABLE'), (httpx.ReadTimeout, 'OPENAPI_TIMEOUT')])
def test_transport_errors(exception, code):
    """连接和超时保留各自错误码，不回显底层异常中的秘密。"""
    def handler(request):
        """模拟传输层失败。"""
        raise exception('secret', request=request)
    api = ApiClient('https://backend.test')
    api.client.close()
    api.client = httpx.Client(base_url=api.endpoint, transport=httpx.MockTransport(handler))
    try:
        with pytest.raises(ApiClientError) as caught:
            api.get_openapi_schema()
        assert caught.value.code == code
        assert 'secret' not in caught.value.message
    finally:
        api.close()
