# 资源与设计系统

资源、主题、字体和样式是页面生成的输入，不是代码完成后的装饰。先查询真实对象，再决定引用、创建或修改。

## 资源选择

查询资源时至少关注 `name`、`asset_type`、`render_type`、`content_editable`、版本/状态、标签和近似宽高比：

| `render_type` | 页面源码优先使用 |
| --- | --- |
| `image` | `AssetImage` |
| `video` | `AssetVideo`，必要时使用真实 poster |
| `drawio` | `AssetDrawio` |
| `mermaid` | `AssetMermaid` |
| `chart` | `AssetChart` |
| `formula` | `AssetFormula` |
| `icon` | `Icon` |
| 自定义图片/背景 URL | `useAssetSrc` / `useAssetBackground` |

先查资源，再写 name；不要根据文件名猜资源逻辑名。资源槽位匹配近似宽高比，完整展示优先 `contain`，只有用户明确要求时才 `cover`。

资源组件的外层必须通过完整静态 class 声明明确宽高，例如 `w-full h-64 rounded-lg border border-border overflow-hidden`。不要给 `Asset*` 传 `style`，不要只靠内容自由撑高、`min-h`、`max-height` 或外层裁切。`AssetImage` 的 class 控制外层图片框，`fit`/`position` 控制图片在框内的显示。

普通资源 URL 使用 `useAssetSrc`，背景使用 `useAssetBackground`；资源名来自 props 时使用 getter。`resolveResourcePath` 只适合非响应式代码，不要在 SFC 中直接解析动态 props。

`Icon` 和 `Asset*` 的 `name` 必须是字符串字面量，或来自同一 Vue 文件顶层的静态枚举；禁止 computed、函数返回、字符串拼接或条件表达式生成资源名。图标名必须等于资源逻辑名，优先查询现有图标再创建。

## 创建或上传资源

```bash
wp --json asset list
wp asset create --payload-file ./asset.json --content-file ./asset-content.txt --idempotency-key <key>
wp asset upload ./image.png --type image --name hero-image --idempotency-key <key>
```

文本资源创建前查询是否已有 active 同名资源。可创建的文本类型包括 SVG 图标/图片、Draw.io、Mermaid、Chart 和 Formula；内容必须是完整 UTF-8 文本，并按命令帮助和 Backend Schema 满足扩展名及安全约束。图标 SVG 不得包含 script、事件属性、`foreignObject` 或远程引用，优先使用 `currentColor`。

非 SVG 位图、video、font 等使用 `asset upload`；不要用 `asset create` 伪造二进制内容，也不要把 URL、本地路径或 base64 当成可信上传附件参数。生成或上传后用返回的真实 name/ID 和 render_type。

## 主题

主题负责共享视觉语义和色板。多页统一视觉时优先使用主题类，不要在每页硬编码品牌色；现有主题与用户目标不匹配时再复制或创建主题。

- 创建主题必须指定稳定、未占用的 `key`；key 创建后不可修改。
- 主题维护只使用 CLI 公开的名称、说明和色板字段；不要猜测或写入 Logo、字体、字体族 ID。
- 主题 palette 使用公开的 `text`、`background.default/invert`、`border`、`link` 和 `accent` 结构；不要把 Tailwind 类名、`background-subtle` 或 `tertiary` 当成主题 Schema 字段。

## 字体

先 `wp font list` 查询已注册字体。主题字体优先使用 `font-heading`、`font-body`、`font-code`；非主题字体必须是工作空间真实注册并下发的字体逻辑名，用 `useAssetFontFamily`，不要在页面 CSS 中写 `@font-face` 或硬编码字体文件 URL。

## 样式和项目配置

样式是可复用的项目展示配置模板，可能包括画布、基础字号、主题 key、样式规范和建议组件。应用样式到项目后形成独立快照；单项目微调直接更新项目 configuration，不要为一次性变化创建全局样式。

修改主题 key、画布、基础字号、样式规范或建议组件前，先读取最新 configuration。主题/字体/样式修改会影响多个页面或项目，写入前明确影响范围和用户目标。
