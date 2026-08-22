# 校验与交付

页面和组件写入由 Backend 的 Mutation Job 负责编译、渲染和布局检查。外部 Agent 的职责是提交正确基线、等待终态、读取结果并用截图验证真实视觉。

## 候选校验和写入校验

独立校验适用于：写入前检查一份候选 SFC、结构化 edits，或失败后请求详细诊断：

```bash
wp --json page validate <page_id> --mode content --source-file ./Page.vue --detail
wp --json page validate <page_id> --mode edits --edits-file ./edits.json --detail
wp --json component validate <component_id> --mode content --source-file ./Component.vue --detail
```

`current` 检查当前内容，`content` 检查完整候选源码，`edits` 检查基于当前对象的结构化编辑；具体参数以命令帮助为准。校验不通过是诊断结果，不是写入成功。

### `edits.json` 格式

`--edits-file` 必须指向一个 JSON 数组。数组中的每个对象都必须包含 `type`，且只能使用以下三种编辑类型：

| `type` | 必填字段 | 作用 |
| --- | --- | --- |
| `replace_exact` | `old_text`、`new_text` | 唯一命中 `old_text` 后替换为 `new_text`；`new_text` 可以为空字符串。 |
| `insert_after` | `anchor_text`、`new_text` | 在唯一命中的 `anchor_text` 后插入 `new_text`。 |
| `rewrite_file` | `content` | 用完整的 `content` 重写源码文件。 |

例如，`replace_exact` 的编辑文件是：

```json
[
  {
    "type": "replace_exact",
    "old_text": "旧文本",
    "new_text": "新文本"
  }
]
```

`old_text` 和 `anchor_text` 必须来自最新源码，并且在应用当时各自唯一命中。`replace_text`、`replace` 等未列出的类型不受支持。

页面/组件创建、源码编辑以及组件复杂 metadata 更新本身会自动校验。成功写入后不必为了“证明已经校验”重复调用同一 `validate`；应重新读取对象并截图。失败时优先使用返回的短 `code`、`message`、定位、`scenario` 和 `profile`，需要更多事实再加 `--detail`。

## Job 状态与处理

```bash
wp --json job get <job_id>
wp --json job wait <job_id> --timeout 120
```

终态只有 `succeeded`、`failed`、`canceled`；`pending` 和 `running` 仍在执行。`succeeded` 后重新读取页面/组件；`failed`/`canceled` 必须保留 Job ID、错误码、错误消息和诊断摘要，不能把部分返回当成完成。

人工重试前确认平台明确允许 retry。网络超时或暂时性 5xx 只对安全请求有限重试；版本冲突、权限错误、参数错误、资源缺失先重新读事实并修正。重试不同业务请求不得复用幂等键。

## 视觉复核

成功后获取最新截图：

```bash
wp page screenshot <page_id> --output .tmp/page.png
```

检查：

- 固定画布是否完整，底部或侧边是否裁切；
- 标题、正文、数字、表格是否可读，长文案是否换行失控；
- 视觉焦点、阅读顺序、主体区域垂直平衡和留白是否有意；
- 主题颜色、字体、Logo、Icon、图片和图表是否真实加载；
- 空态、缺图、数据不足、错误提示和默认组件态是否仍然成立。

截图发现问题时优先对当前版本做最小结构化编辑；重新读取版本基线后再提交，不要以旧源码生成新 edits。

## 最终汇报

至少说明：

- 工作空间、项目、页面/组件的真实 ID；
- 执行的创建/编辑/配置/发布/归档动作；
- 页面或组件版本、组件发布版本、Job ID 和幂等键（如用户需要追踪）；
- 校验结果、截图路径和视觉复核结论；
- 未执行的动作、失败原因、未验证项或需要用户补充的资料。

只完成查询、候选校验或方案时，明确写“未写入”；不要用计划、预期任务或模型推断冒充平台事实。
