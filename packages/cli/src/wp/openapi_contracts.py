"""文件功能：严格解析命令请求契约及可达本地引用，供帮助和 Doctor 共用。"""

from typing import Any

from wp.client import ApiClientError


def render_contract(document: dict, contract: Any) -> dict:
    """提取单个操作，拒绝缺失操作、畸形参数和不能解析的引用。"""
    details = {'stage': 'contract', 'method': contract.method, 'path': contract.path}

    def fail(message: str, location: str, code: str = 'OPENAPI_REFERENCE_INVALID') -> None:
        """保留失败的请求位置，便于定位服务端契约漂移。"""
        raise ApiClientError(message, code=code, details={**details, 'location': location})

    references: dict[str, Any] = {}

    def visit(value: Any, location: str) -> None:
        """解析本地 JSON Pointer，先登记再递归以支持循环 Schema。"""
        if isinstance(value, dict):
            if '$ref' in value:
                ref = value['$ref']
                if not isinstance(ref, str) or not ref.startswith('#/components/'):
                    fail('不支持的 OpenAPI 引用。', location + '/$ref')
                target: Any = document
                for segment in ref[2:].split('/'):
                    key = segment.replace('~1', '/').replace('~0', '~')
                    if not isinstance(target, dict) or key not in target:
                        fail(f'OpenAPI 引用不存在：{ref}', location + '/$ref')
                    target = target[key]
                if not isinstance(target, dict):
                    fail(f'OpenAPI 引用目标必须是对象：{ref}', location + '/$ref')
                if ref not in references:
                    references[ref] = target
                    visit(target, ref)
            for key, child in value.items():
                visit(child, f'{location}/{key}')
        elif isinstance(value, list):
            for index, child in enumerate(value):
                visit(child, f'{location}/{index}')

    def resolved(value: dict) -> dict:
        """跟随已检查的组件引用；请求对象本身不允许循环引用链。"""
        seen = set()
        while '$ref' in value:
            ref = value['$ref']
            if ref in seen:
                fail('请求对象引用链循环。', ref)
            seen.add(ref)
            value = references[ref]
        return value

    def check_content(owner: dict, location: str) -> None:
        """校验媒体类型映射和 Schema 入口，拒绝被忽略的畸形内容。"""
        content = owner.get('content')
        if not isinstance(content, dict) or not content:
            fail('OpenAPI content 必须是非空对象。', location + '/content')
        for media_type, media in content.items():
            if not isinstance(media, dict):
                fail('媒体类型内容必须是对象。', location + '/content/' + media_type)
            if 'schema' in media and not isinstance(media['schema'], (dict, bool)):
                fail('媒体类型 Schema 必须是对象或布尔值。', location + '/content/' + media_type + '/schema')

    path_item = document.get('paths', {}).get(contract.path)
    if not isinstance(path_item, dict) or not isinstance(path_item.get(contract.method.lower()), dict):
        fail('OpenAPI 缺少命令所需路径或方法。', contract.path, 'OPENAPI_OPERATION_MISSING')
    operation = path_item[contract.method.lower()]
    parameters = []
    for owner, location in ((path_item, contract.path), (operation, contract.path + '/' + contract.method.lower())):
        if 'parameters' in owner:
            value = owner['parameters']
            if not isinstance(value, list) or any(not isinstance(item, dict) for item in value):
                fail('OpenAPI parameters 必须是对象数组。', location + '/parameters')
            parameters.extend(value)
    body = operation.get('requestBody')
    if 'requestBody' in operation and not isinstance(body, dict):
        fail('OpenAPI requestBody 必须是对象。', contract.path + '/requestBody')
    result = {'parameters': parameters, 'requestBody': body}
    visit(result, contract.path + '/' + contract.method.lower())
    for index, parameter in enumerate(parameters):
        parameter = resolved(parameter)
        location = contract.path + f'/parameters/{index}'
        if not isinstance(parameter.get('name'), str) or parameter.get('in') not in ('path', 'query', 'header', 'cookie'):
            fail('请求参数缺少合法 name/in。', location)
        if 'schema' in parameter and not isinstance(parameter['schema'], (dict, bool)):
            fail('参数 Schema 必须是对象或布尔值。', location + '/schema')
        if 'content' in parameter:
            check_content(parameter, location)
    if body is not None:
        check_content(resolved(body), contract.path + '/requestBody')
    if references:
        result['referencedSchemas'] = {ref.rsplit('/', 1)[-1]: value for ref, value in references.items()
                                       if ref.startswith('#/components/schemas/')}
        result['referencedComponents'] = references
    return result


def validate_registered_contracts(root: Any, document: dict) -> None:
    """遍历真实 Click 注册树，不维护第二份接口清单。"""
    def visit(command: Any, path: str) -> None:
        """校验叶子全部操作，为错误补充命令路径。"""
        for contract in getattr(command, 'openapi_contracts', ()):
            try:
                render_contract(document, contract)
            except ApiClientError as exc:
                exc.details = {**(exc.details or {}), 'command': path}
                raise
        for name, child in getattr(command, 'commands', {}).items():
            visit(child, f'{path} {name}')
    visit(root, root.name or 'wp')
