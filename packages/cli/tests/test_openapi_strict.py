"""文件功能：验证严格契约帮助、循环引用和 Doctor 错误退出语义。"""

import json

import pytest
from click.testing import CliRunner

from wp.cli import main
from wp.client import ApiClient, ApiClientError
from wp.openapi_help import contract
from wp.openapi_contracts import render_contract


@pytest.mark.parametrize('document,code', [
    ({'paths': {}}, 'OPENAPI_OPERATION_MISSING'),
    ({'paths': {'/x': {'post': {'parameters': {}}}}}, 'OPENAPI_REFERENCE_INVALID'),
    ({'paths': {'/x': {'post': {'requestBody': {'$ref': '#/components/schemas/Missing'}}}}}, 'OPENAPI_REFERENCE_INVALID'),
    ({'paths': {'/x': {'post': {'requestBody': {'$ref': 'https://external/schema'}}}}}, 'OPENAPI_REFERENCE_INVALID'),
])
def test_invalid_contract(document, code):
    """畸形或缺失契约必须失败，不能静默丢弃字段。"""
    with pytest.raises(ApiClientError) as caught:
        render_contract(document, contract('POST', '/x'))
    assert caught.value.code == code
    assert caught.value.details['location']


def test_circular_reference():
    """合法递归 Schema 能完整收集且不无限递归。"""
    ref = {'$ref': '#/components/schemas/Node'}
    document = {'paths': {'/x': {'post': {'requestBody': {'content': {'application/json': {'schema': ref}}}}}}, 'components': {'schemas': {'Node': {'properties': {'next': ref}}}}}
    assert 'Node' in render_contract(document, contract('POST', '/x'))['referencedSchemas']


def test_json_help_failure_has_no_partial_stdout(monkeypatch):
    """多操作任一分支缺失时，所有帮助都不输出。"""
    monkeypatch.setattr(ApiClient, 'get_openapi_schema', lambda *a, **k: {'paths': {'/api/v1/components/{component_id}': {'patch': {}}}})
    result = CliRunner().invoke(main, ['--json', 'component', 'update', '--help'])
    assert result.exit_code == 1
    assert result.stdout == ''
    assert json.loads(result.stderr)['code'] == 'OPENAPI_OPERATION_MISSING'


@pytest.mark.parametrize('args', [['doctor'], ['--json', 'doctor']])
def test_doctor_contract_error(monkeypatch, tmp_path, args):
    """健康正常不覆盖契约失败，文本和 JSON 都非零退出。"""
    import wp.config as config
    import httpx
    monkeypatch.setattr(config, 'CONFIG_FILE', tmp_path / 'config.json')
    monkeypatch.setattr('wp.commands.doctor.httpx.get', lambda *a, **k: httpx.Response(200, json={'status': 'ok'}))
    def fail(*args, **kwargs):
        """模拟网关错误返回 HTML。"""
        raise ApiClientError('响应是 HTML', code='OPENAPI_CONTENT_TYPE_INVALID', details={'content_type': 'text/html'})
    monkeypatch.setattr(ApiClient, 'get_openapi_schema', fail)
    result = CliRunner().invoke(main, args)
    assert result.exit_code == 1
    assert 'HTML' in result.stdout
