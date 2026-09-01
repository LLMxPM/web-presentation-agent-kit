# 页面生成流程

本参考用于“从内容目标生成一页或一组演示页面”。页面是固定尺寸的二维画布：先完成信息与空间构图，再写 Vue SFC，最后提交平台任务并视觉复核。

## 1. 从需求形成页面 brief

先在内部明确，不必把草稿过程原样输出：

- 受众与使用场景；
- 本页唯一主要结论；
- 标题、眉题、正文、数字、引用、来源和演讲者备注；
- 内容最适合用文字、表格、图表、示意图还是图片表达；
- 画布方向、信息密度、品牌/主题、可复用组件和必须使用的素材；
- 缺失资料的明确占位，以及空态、加载态、错误态、超长文本和缺图状态。

一个页面优先讲清一个主要信息。不要为了填满画布增加无关卡片、装饰或虚构数据。

## 2. 读取工作区和项目基线

推荐顺序：

```bash
wp --json workspace capabilities --workspace-id <workspace_id>
wp --json project get <project_id>
wp --json project configuration get <project_id>
wp --json project route get <project_id>
wp --json page list --project-id <project_id>
wp --json component list --scope suggested --project-id <project_id>
wp --json asset list
wp --json theme list
wp --json style list
wp standards page
wp runtime-kit list
```

如果目标是已有页面，再读取：

```bash
wp --json page get <page_id>
wp --json page source <page_id>
wp --json page dependencies <page_id>
```

项目 configuration 决定真实画布宽高、基础字号、主题 key、样式规范和建议组件。`base_font_size` 替代 Tailwind 默认 16px 基准，语义字号和间距按 `base_font_size / 16` 理解；直接写入的 px、rem 和 arbitrary value 不参与这个倍率。

## 3. 先决定复用还是新建

按这个优先级处理：

1. 项目建议的已发布页面组件；
2. 当前工作空间内其它已发布页面组件；
3. 直接使用 Runtime Kit 的 `DefaultContainer`；使用前通过 `wp runtime-kit get <item>` 获取真实版本化 import path。

页面组件不仅用于封面、目录、章节分隔或页面骨架，也用于具有重复标题区、眉题/导航、主体区和辅助区空间关系的内容页模板、报告页模板和数据页模板。如果同一任务包含两个或以上结构相近的内容页，或用户明确要求多页保持统一版式，即使正文、图表和数据不同，也应优先查询并复用页面组件；没有合适组件时创建 `component_type=页面组件` 的内容页模板，通过 props/slots 接收可变标题和主体内容。重复的是版式结构，不是同一段标题文案，不要因为正文不同就把共有页面壳复制到各页面源码中。指标卡、引用卡、图表和表格只有在职责稳定、会重复且可由 props/slots 表达时才沉淀为内容组件；当前页面独有的叙事包装留在页面源码中。

## 4. 形成固定画布构图

组件复用判断与页面布局判断是两个独立步骤：先选定或创建重复内容页模板，再在页面组件或页面源码内部将画布划分为标题区、主体区和辅助区，明确每个主要内容组的空间锚点、宽高、对齐、层级和 overflow 策略。标题可以顶部对齐，但主体面板和稀疏卡片默认应在自己的可用高度内平衡，不要让正文堆在顶部、再用 `mt-auto` 把尾部推到底部。

可以使用非对称布局、跨区排版、重叠、分层背景、旋转和有意出血；装饰可以被画布裁切，关键信息不能被裁切。内容放不下时按“精简信息 → 改变表现形式 → 重新构图 → 调整分区 → 拆分页面”处理。

禁止用 `100vh`、`100vw`、页面长滚动、`zoom` 或 `transform: scale` 规避固定画布。`flex-1` 只用于已规划的区域，不用于制造空白；`justify-center` 应用于正确的内容组，而不是无差别包住整页。

## 5. 编写页面 SFC

页面必须是完整、可运行的 Vue 3 SFC。默认根结构：

```vue
<script setup lang="ts">
import DefaultContainer from '@runtime-kit/public/components/page/layout/DefaultContainer.v1.vue'
</script>

<template>
  <DefaultContainer>
    <main class="relative h-full">
      <section class="absolute inset-0 p-16">
        <!-- 先实现已经规划好的页面结构，再填入真实内容。 -->
      </section>
    </main>
  </DefaultContainer>
</template>
```

实际 import path 必须以 `wp runtime-kit get` 返回为准；页面规范、主题类、资源组件和禁止项见 [页面源码规范](./source-standards.md)。

## 6. 预检和写入

修改已有页面时，先读取最新源码并生成基于真实片段的结构化 edits，再使用当前版本：

```bash
wp page validate <page_id> --mode content --source-file ./Page.vue
wp page edit <page_id> \
  --base-version-no <current_version_no> \
  --edits-file ./edits.json \
  --idempotency-key <key>
```

`edits.json` 必须使用当前 `wp page edit --help` 显示的结构化编辑 Schema；匹配片段来自最新源码且必须唯一命中。

新建页面使用完整 SFC：

```bash
wp page create --project-id <project_id> --name "核心结论" --file ./Page.vue --idempotency-key <key>
```

页面标题、摘要、演讲者备注等轻量字段使用 `wp page update`；不要用 metadata 更新命令承载源码。页面创建和源码编辑会自动执行编译、渲染和布局校验；独立 `page validate` 用于候选预检或需要更多诊断，不是绕过平台写入校验的办法。

## 7. 成功后的复核

任务成功后按顺序：

```bash
wp --json page get <page_id>
wp --json page source <page_id>
wp page screenshot <page_id> --output .tmp/page.png
```

检查截图中的画布尺寸、底部裁切、文字换行、视觉重心、资源加载、空态/缺图和真实内容密度。发现问题时优先做局部 edits，不要无证据地重写整页。
