---
name: web-presentation
description: Use the web-presentation External API v1 through the wp CLI to plan, create, inspect, validate, and refine fixed-canvas presentation pages and reusable components with the platform's themes, assets, Runtime Kit, and async jobs.
---

# Web Presentation

这是一个面向演示页面创作的 CLI Skill。它指导 Agent 如何把用户的内容目标转化为当前工作空间内可运行、可校验、可复用的页面和组件；不把 Web Presentation 当作普通文件系统、自由执行代码的环境或通用网页脚手架。

本 Skill 的内容与构图约束是 Skill 自己的工作方法。平台操作指南、校验结果和公开能力是执行时的事实来源，但不改变本 Skill 的组织方式。需要确认 CLI 参数时读取 [CLI 调用参考](./references/cli-usage.md)，复杂操作以 `wp guide` 和当前 CLI 帮助为准。

## CLI 最小入口

全局选项放在子命令之前：

```bash
wp --json --workspace <workspace_id> workspace capabilities
wp --json --workspace <workspace_id> project list
```

每轮任务先执行或确认：

```bash
wp whoami
wp workspace list
wp workspace use <workspace_id>
wp guide
```

没有明确唯一工作空间、目标对象 ID 或当前版本基线时，不执行写入。自动化场景优先使用 `--json`，不要依赖表格文案解析。

## 一、先理解内容，再设计页面

生成或修改页面前，先从用户需求中提取：

- 受众、使用场景和页面目标；
- 本页唯一主要信息或结论；
- 必须保留的事实、数字、引用、来源和素材；
- 期望的页面类型、画布方向、风格和品牌约束；
- 是否需要跨页复用的组件、主题、资源或样式。

只有缺少必要业务信息且不同选择会显著改变结果时才询问用户。资料不足时使用明确占位或说明缺口，不能凭空编造事实、指标、引用、客户名称、Logo 或业务结果。

一个页面优先讲清一个主要结论：

- 标题应尽量结论化，眉题、导航和辅助信息服从主叙事；
- 用文字、表格、图表、示意图或图片表达最适合的信息，不要把所有内容都堆成卡片；
- 控制信息密度，避免为填满画布堆砌段落、装饰和无关模块；
- 为真实内容考虑空态、加载态、错误态、超长标题、缺图和数据不足等状态；
- 页面整体应有清晰的视觉重心、阅读顺序和跨页一致性。

## 二、固定画布与构图约束

Web Presentation 的页面是固定尺寸的演示画布，不是可以随着内容自然变高的网页文档。实现前先根据项目配置确认画布宽度、高度和基础字号，再规划标题区、主体区、辅助区和安全边距。

- 主体内容区、内容面板和稀疏卡片默认在自身可用高度内上下平衡；不要让内容无理由堆在顶部或被 `mt-auto` 推到最底部。
- 大面积留白必须有构图目的，例如封面留白、章节分隔、海报式焦点或固定页脚；不能用空白掩盖内容规划不足。
- 优先形成整页构图，再实现具体卡片和元素；空间规划不是把画布机械切成互不重叠的矩形。
- 避免 `100vh`、`100vw`、`zoom`、`transform: scale` 和无边界的网页式长滚动；不要让内容超出固定画布或被固定高度裁切。
- 视觉复杂性应来自有意的层级、比例、留白和信息关系，而不是无意义的渐变、阴影、圆角和装饰。
- 需要视觉确认时必须获取最新截图，检查溢出、文字可读性、主体重心、资源加载、空态/加载态/错误态和真实内容下的平衡。

## 三、优先利用平台资产

工作空间是权限、数据隔离和共享资产边界。项目、页面、组件、资源、主题和样式都必须属于当前工作空间；名称只用于理解和搜索，实际操作必须使用查询结果中的真实 ID。

按以下优先级组织页面：

1. 读取目标项目的配置、画布、基础字号、主题、样式和建议组件。
2. 查询并复用当前工作空间已经发布的页面组件、内容组件、原子组件和资源。
3. 复用现有主题的语义色和现有样式的展示基线；只有现有资产无法表达用户明确目标时，才创建新的主题或样式。
4. 找不到合适资源时再上传或创建资源；需要标识性图形时优先查询工作空间图标，避免在页面源码中临时绘制重复 Logo 或图标。
5. 只有稳定职责、会跨页面复用且变化可以由 props/slots 表达的结构才沉淀为组件；只服务当前页面叙事的一次性包装保留在页面源码中。

页面组件负责整页结构，内容组件负责卡片、图表、表格、指标区等可复用内容块，原子组件负责按钮、徽章、头像、分割线等单一职责元素。组件应先形成稳定草稿并通过校验，发布后页面和其他组件才引用其正式版本。

主题负责视觉语义和色板，样式负责画布、字号、主题和建议组件等展示配置。样式应用到项目后形成独立快照，不要假设后续修改样式会自动改变已应用项目。主题、样式和组件的创建或修改都只做用户目标所需的最小范围变更。

## 四、页面源码规范

页面源码必须是完整、可运行的 Vue 3 SFC，不是 HTML 片段、Markdown、JSON 配置或说明文字。页面是固定尺寸的二维演示画布；实现前读取项目 configuration，遵循真实画布尺寸、基础字号、安全边距和样式基线。

### 页面先构图，再写代码

- 把整张页面或页面组件提供的 slot 区域视为一个有明确边界的完整空间，先确定主要信息、视觉焦点、阅读动线、视觉重心、对齐关系、留白、资源占位和尺寸关系，再实现元素。
- 禁止采用“先放标题，再向下追加段落、卡片、图片和页脚”的网页文档式生成顺序；Flex、Grid、绝对定位和分层布局都应实现已规划的空间关系，不应让内容自然撑开整页。
- 先划分标题区、主体区和辅助区。标题、眉题和导航可以顶部对齐，但主体内容区、内容面板和稀疏卡片默认应在各自可用高度内上下平衡；不要把整个页面机械地 `justify-center`。
- 对 `flex-col`，垂直方向由 `justify-*` 控制，水平方向由 `items-*` 控制；对 Grid，垂直居中使用 `place-items-center` 或 `items-center`。`text-center` 只改变文字对齐，不会使容器内容上下居中。
- `flex-1` 只用于分配已经规划好的页面区域，不得用来制造空白或拉伸稀疏卡片。不要把 `grid/flex-1`、固定高度、顶部排列和 `mt-auto` 组合成默认卡片结构；`mt-auto`、`space-between`、`space-around` 只能用于明确的页脚、上下锚点或对照构图。
- 内容无法填满容器时，优先将完整内容组垂直居中、缩小容器、调整分区或精简信息；表格、目录、长文、时间线、密集数据和明确的顶部引导版式可以顶部对齐。
- 空间规划不等于机械切成互不重叠的矩形。可以使用非对称构图、自由定位、跨区排版、元素重叠、分层背景、旋转和装饰性出血；装饰可被画布裁切，但关键信息必须完整、清晰、可读。
- 主要内容、分栏、卡片、图表、图片区和公式区必须有可判断的空间锚点、宽高上下文、flex/grid 约束、overflow 策略和留白。依赖 `h-full` 的子元素必须具备明确的父级高度。
- 内容无法在既定构图中成立时，按“精简信息 → 改变表现形式 → 重新构图 → 调整分区 → 拆分页面”的顺序处理；不使用 `100vh`、`100vw`、页面滚动、内容自然撑高、`transform: scale` 或 `zoom` 逃避布局约束。
- 大幅改写页面前先在内部形成画布构图方案，检查画布方向、安全边距、视觉焦点、阅读动线、空间锚点、层级、资源占位、留白、文字容量、固定高度和潜在溢出；不需要暂停等待用户确认，也不默认输出内部草稿。

`base_font_size` 替代 Tailwind 默认 16px 基准。`text-*`、`p-*`、`m-*`、`gap-*`、`space-*` 等语义字号和间距按 `base_font_size / 16` 理解整体倍率；直接写入的 px、rem 和 Tailwind arbitrary values 不参与该倍率。

### 页面根结构与复用

- 页面根节点优先使用项目建议的已发布页面组件，其次查询工作空间内已发布页面组件，最后才直接使用 Runtime Kit 的 `DefaultContainer`；直接使用前先查询真实的版本化 `import_path`。
- 开始创建页面时先查询并复用已有页面组件。只有封面、目录、章节分隔或页面骨架等具有明确模板价值、预计跨页或跨项目复用的结构才创建页面组件。
- 如果指标卡、引用卡、图表或表格模块会跨页重复，且变化可以用稳定 props/slots 表达，再沉淀为内容组件；当前页面独有的一次性排版和包装容器留在页面源码中。
- 不要为了预先抽象、减少当前文件长度或替换一小段局部标记而拆分组件。

### 页面校验结果判读

- 优先处理校验返回的 code、message、定位、布局类别计数和真正影响可读性的错误/警告；不能把所有几何提示机械当成错误。
- `PAGE_RENDER_BOTTOM_OVERFLOW` 表示固定画布底部可能裁切，应压缩内容、调整容器高度或拆分页面；warning 也要判断是否会影响完整性。
- `interior_gap`、`trailing_gap` 与 `sparse_top_aligned` 同时出现时，默认检查 `mt-auto`、固定高度和顶部堆叠，优先改为局部垂直居中、取消自动 margin 或重新规划容器高度。
- `empty_regions` 需要结合安全边距、栅格、容器尺寸和页面类型判断；封面、章节页、海报式构图和对称居中留白不应机械压缩。
- 正常多行正文、正常 `flex-wrap` 分排、组合容器中紧贴的圆角子项和有意的装饰出血不应单独修复。`geometry_reliability=approximate` 时要结合截图判断旋转或 `clip-path` 的实际语义。

## 五、组件源码规范

组件 content 也必须是完整、可运行的 Vue 3 SFC。先按职责选择正确的 `component_type`：

- 页面组件：负责封面、目录、章节页、页面骨架或整页视觉结构，以 `DefaultContainer` 或已发布页面骨架为根，具备独立的整页画布承载能力，不依赖父页面偶然提供的 `h-full/w-full` 高度上下文；通过 props 或具名 slot 接收变化，不硬编码具体页面文案。
- 内容组件：负责卡片、图表、指标组、表格、资源展示块和普通业务区块；必须在 `preview_schema.props` 中声明至少一个尺寸控制字段，例如 `width`、`height`、`minHeight` 或 `aspectRatio`，并处理默认数据、空态、长文本和溢出。
- 原子组件：负责页码、角标、图标、主题 Logo、小标签和装饰符号等单一职责小单元；优先提供 `size`、`density`、`variant`、`tone` 等语义参数，不默认暴露裸 `fontSize`/`padding` 数值 props。

所有组件必须提供合法的 `preview_schema`：

- Schema 字段必须与 Vue `defineProps` 保持一致，包含必要的 type、label 和 default；`preview_schema` 要与真实 props、slots、mocks 对齐，预览值不能混在 Schema 根节点。
- 优先提供 2～3 个高质量 presets，覆盖真实使用场景，而不是堆叠大量低质量变体。
- 资源名、默认值和 mock 数据必须来自真实工具结果；没有合适资源时使用空值或清晰占位，不编造资源名称。
- 组件不绑定当前项目的具体画布尺寸、基础字号或 palette；跨页面复用的变化用 props/slots 表达，不能把当前项目内容写死。
- 修改组件源码、`component_type` 或 `preview_schema` 前读取最新草稿和版本基线，使用结构化 edits 或完整候选内容完成修改；发布前确认默认态、预览 presets 和布局诊断结果。

## 六、主题、字体、资源与 Runtime Kit 规范

页面和组件都必须遵守同一套公开视觉能力边界：

- Runtime 主题语义颜色键只包括 `primary`、`secondary`、`invert`、`background`、`background-subtle`、`background-invert`、`border`、`border-subtle`、`link`、`link-hover`、`link-visited` 和 `accent1` 至 `accent6`；不得猜测其它语义键或硬编码品牌资源。
- `background-subtle` 是 Runtime 提供的语义背景槽位，不是主题写入 Schema 中的 `palette.background.subtle` 字段。
- 字体语义类使用 `font-heading`、`font-body`、`font-code`；需要非主题字体时先查询工作空间字体，再使用 Runtime Kit 的 `useAssetFontFamily`。主题 Logo 优先使用 `ThemeLogo`，不要硬编码资源路径。
- 直接写 CSS 时优先使用公开 Runtime 桥接变量，如 `--tw-color-text-primary`、`--tw-color-bg-default`、`--tw-color-bg-subtle`、`--tw-color-bg-invert`、`--tw-color-border-default`、`--tw-color-link-default`、`--tw-color-accent1`、`--tw-font-body`；不要猜测 `--color-*` 或其它未公开变量。`ThemeLogo` 优先只通过 `size` 控制等比高度，不传 `width`、`height` 或 `fit`。
- Tailwind class 必须以完整静态字符串出现在模板、脚本常量或顶层枚举映射中；可以使用平台 safelist 支持的常用工具类和静态 arbitrary values，但不能拼接 `text-${tone}`、`from-${color}` 或运行时生成 import。
- 使用素材前查询 active 资源的 `render_type`、`content_editable`、版本和近似宽高比，再选择 `AssetImage`、`AssetVideo`、`AssetDrawio`、`AssetMermaid`、`AssetChart`、`AssetFormula` 或 `Icon`。资源槽位匹配资源宽高比，完整展示优先 `contain`，只有用户明确要求时才使用 `cover`。
- `AssetImage`、`AssetVideo`、`AssetDrawio`、`AssetMermaid`、`AssetChart` 和 `AssetFormula` 的资源容器必须通过完整静态 class 明确宽高；不要给 `Asset*` 传 style，也不要只依赖内容自由撑高、`min-h`、`max-height` 或外层 `overflow-hidden`。
- `AssetImage` 的 class 作用于外层图片框，图片内容用 `fit="contain"`/`fit="cover"` 和 `position` 控制；纵向长图必须在 AssetImage 自身 class 上提供确定高度，例如 `h-[500px]` 或父级高度明确时的 `h-full`。
- `Icon` 和 `Asset*` 的 `name` 使用字符串字面量，或来自同一 Vue 文件顶层可静态枚举的对象/数组；不得使用 computed、函数返回、字符串拼接或条件表达式动态生成资源名。
- 普通资源 URL 使用 `useAssetSrc`，背景资源使用 `useAssetBackground`；资源名来自 props 时传入 getter，例如 `useAssetSrc(() => props.imageName)`。`resolveResourcePath` 仅用于非响应式工具代码或 Runtime public 静态路径，不要在 SFC 中直接解析动态 props。
- 背景图和蒙版作为画布内独立视觉层：背景层使用 `absolute inset-0 h-full w-full`，正文放在 `relative z-10 h-full w-full` 等更高层级；蒙版、渐变和暗角单独实现并设置 `pointer-events-none`。
- 页面与组件只能使用公开且带 `.vN` 版本的 Runtime Kit import、已发布工作空间组件和可见工作空间资源；不能猜测不存在的 API、组件、Token、CSS 变量或资源。

## 七、从读取到交付的工作流

### 1. 确认范围

确认当前 Profile、工作空间、项目工作集和目标对象。用户只要求分析、建议、解释或审阅时保持只读，不创建、修改、归档或发布对象。

### 2. 读取基线

读取目标项目、页面或组件的最新元数据、配置、源码、版本、依赖、主题、样式和相关资源。复杂操作先用 `wp guide` 查询 operation 的参数、前置条件、幂等要求、副作用和错误恢复方式。

不要仅凭名称推断关联，不要使用无 ID 的“当前页面”或“当前项目”，不要基于旧源码、旧版本或历史截图写入。

### 3. 规划最小变更

先决定是更新内容、调整构图、复用组件、补充资源、维护主题/样式，还是创建新的页面/组件。保留用户未要求改变的结构、内容、风格和配置；不要为了展示能力扩大修改范围。

页面或组件源码任务使用完整候选 SFC 或操作指南规定的结构化编辑。元数据更新使用明确的 `--idempotency-key`；版本、草稿 hash 和对象归属以最新读取结果为准。

### 4. 执行并等待

页面和组件创建、源码编辑等重任务通过平台 Mutation Job 执行。提交后使用：

```bash
wp job mutation get <job_id> --wait --timeout 60
```

只接受 `pending | running | succeeded | failed | canceled` 语义。成功后重新读取对象或截图；失败时保留平台返回的状态、错误码、错误消息和诊断摘要。只有平台明确任务可人工重试时，才执行 `wp job mutation retry <job_id>`；版本冲突、权限错误或参数错误必须先重新读取和修正。

### 5. 校验和视觉复核

使用 `wp validate <file> --type page|component` 做独立源码预检；它是诊断，不是写入替代。写入返回的校验结果优先于本地猜测。需要视觉确认时使用 `wp screenshot <page_id> --output <file>` 获取最新 PNG，并基于真实版本检查布局和资源。

### 6. 汇报真实结果

最终说明完成的对象和动作、工作空间、目标 ID、版本基线、幂等键、任务 ID、校验/截图结果以及仍未验证或失败的事项。没有成功响应不得声称已经创建、更新、发布、归档或校验通过。

## 八、生命周期与安全边界

- 对外 HTTP 公共前缀固定为 `/api/v1`，不使用旧的 `/api/external/v1`。
- 不跨工作空间猜测、复制、读取或写入对象；不绕过平台权限、Schema 校验、版本校验、确认流程或任务队列。
- CLI 的 `archive` 是归档，不是永久删除。默认保留交互确认，只有用户明确授权当前归档动作时才使用 `--yes`。
- 不执行永久删除，不通过修改状态字段伪造删除或恢复，不把归档项目误解为级联归档页面、路由或共享资产。
- 不把 PAT 写入源码、Skill 输出、工具返回、错误消息、日志、命令示例或截图 URL。
- 不直接访问数据库、Redis、Runtime、Chromium 或平台内部服务；不猜测或拼接尚未冻结的 Build、产物下载和部署命令。
- 用户没有要求写入时保持只读；跨焦点写入、批量归档和危险覆盖必须遵守平台确认语义。

## 输出习惯

优先使用 `--json` 和稳定结构化结果。长源码、图片和诊断详情使用文件或受保护的资源链接，不把大段内容塞进普通对话；输出只陈述已经被 CLI 或平台响应证实的事实。
