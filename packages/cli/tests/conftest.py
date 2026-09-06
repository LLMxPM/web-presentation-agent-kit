"""文件功能：为纯 CLI 测试提供注册表派生的传输替身，禁止依赖真实用户服务。"""

import pytest


@pytest.fixture(autouse=True)
def registered_openapi(monkeypatch):
    """默认模拟可达契约；错误和契约细节测试可显式覆盖此替身。"""
    from wp.cli import main
    from wp.client import ApiClient
    document = {'openapi': '3.1.0', 'paths': {}}

    def visit(command):
        """从实际命令收集路径，仅用于不关注请求结构的 CLI 测试。"""
        for contract in getattr(command, 'openapi_contracts', ()):
            document['paths'].setdefault(contract.path, {})[contract.method.lower()] = {}
        for child in getattr(command, 'commands', {}).values():
            visit(child)
    visit(main)
    monkeypatch.setattr(ApiClient, 'get_openapi_schema', lambda *args, **kwargs: document)
