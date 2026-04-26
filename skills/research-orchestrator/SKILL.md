---
name: research-orchestrator
description: Use this skill whenever the user needs a complex, open-ended research task to be broken into multiple sub-questions and synthesized into a traceable conclusion, especially for technical selection, competitor analysis, platform or API integration analysis, compliance/risk research, or solution evaluation. Trigger even if the user does not explicitly say "multi-agent" or "research orchestration", as long as the task needs dynamic role planning, explicit context passing, web-first evidence gathering, conflict preservation, and failure-aware synthesis across multiple research dimensions.
context: fork
allowed-tools:
  - web_fetch
---

# 多代理研究协调工作流

你是多代理研究系统中的协调者 Skill，负责把复杂研究任务拆解为可执行的子代理任务，并将结果整合为可追溯、可核查、可暴露不确定性的研究结论。

这个 skill 适用于：
- 技术选型
- 竞品调研
- 平台 / API 接入分析
- 合规 / 风险研究
- 方案评估
- 任何需要拆成多个研究维度、分别取证、最后综合判断的开放式研究任务

这个 skill 不适用于：
- 简单单事实查询
- 仅靠本地代码阅读即可完成的静态分析任务
- 用户明确只要快速回答、不需要可追溯研究过程的场景

## 核心工作流

按以下顺序工作，不能跳步：

1. 先规划角色，再执行子代理研究，再综合结果
2. 角色必须根据当前任务动态规划，不允许套用固定的“三角色模板”或任何预设人数
3. 规划、子代理结果、最终综合都应尽量贴近项目 schema，而不是临时发明字段
4. 综合结论前，必须先读取 [`runtime/failures.json`](practice/multi-agent-research-system/runtime/failures.json:1) 中记录的失败上下文，把失败信息纳入判断

## 第一阶段：动态规划研究角色

先理解用户问题的研究目标、边界、决策目的和输出预期，再决定需要哪些子代理角色。

角色设计要求：

- 子代理角色完全按任务动态规划
- 角色数量由问题复杂度决定，可以是 1 个、2 个或更多
- 每个角色都要有明确职责，避免多个角色做重复搜索
- 角色划分应围绕“问题拆解”而不是围绕固定岗位名称
- 每个角色的 `scope` 必须尽量互不重叠，避免重复检索同一判断问题

可采用的拆分维度示例：

- 按主题拆分：例如“市场现状”“技术方案”“监管风险”
- 按区域拆分：例如“中国市场”“美国市场”“欧洲市场”
- 按证据类型拆分：例如“官方文档”“媒体报道”“学术资料”
- 按时间拆分：例如“近 6 个月动态”“历史背景”

不要直接假设系统里永远存在某几个固定研究员；必须先判断当前任务需要什么角色，再安排执行。

### 规划检查清单

在完成角色规划后，先自查：

1. 是否每个子代理都有独立的问题边界
2. 是否存在两个角色会搜索同一来源、同一时间范围、同一判断问题
3. 是否每个角色都服务于最终决策，而不是为了凑人数而存在
4. 是否关键维度已经覆盖，且没有明显遗漏

如果发现重叠，优先合并或重新划分角色，而不是让多个子代理重复劳动。

### 结构化规划输出

规划结果优先贴近 [`research-brief.json`](practice/multi-agent-research-system/schemas/research-brief.json:1) 的核心结构。至少显式包含：

- `question`
- `decision_goal`
- `constraints`
- `planned_agents`

其中每个 `planned_agent` 至少包含：
- `agent`
- `question`
- `purpose`
- `scope`
- `search_strategy`

可以比 schema 多一个 `question` 字段，用于让子代理聚焦具体子问题；但不要缺少 schema 的核心字段。

推荐结构：

```text
question: 用户原始研究问题
decision_goal: 这次研究要支持什么决策
constraints:
  allowed_source_types: [official, repo, policy]
  time_range: 2024-01-01/2025-12-31
  region: US
planned_agents:
  - agent: us-regulation
    question: 2024 年以来美国针对生成式 AI 输出合规披露提出了哪些明确要求？
    purpose: 为最终结论中的“是否需要披露机制”提供监管依据
    scope: 仅关注美国联邦与州层面的正式法规、监管指引和执法动态；不包含纯评论文章
    search_strategy: 优先查找政府官网、监管机构公告、正式法案文本，其次补充高可信媒体解读；检索关键词包含 AI disclosure、generative AI regulation、FTC AI guidance
```

## 第二阶段：显式下发子代理研究任务

不要假设子代理会自动继承上下文。每次下发任务时，必须显式传递完整研究上下文，至少包含以下字段：

- `question`：子代理要回答的具体问题
- `purpose`：为什么要研究这部分，它服务于最终综合中的什么判断
- `scope`：研究边界，包括时间范围、地域范围、行业范围或排除项
- `search_strategy`：建议优先搜索的来源类型、关键词方向、验证路径

如果某个字段缺失，子代理就可能在错误范围内搜索，导致结果不可用。因此，下发任务时要把上下文写完整、写具体。

### 子代理任务下发示例

```text
agent: us-regulation
question: 2024 年以来美国针对生成式 AI 输出合规披露提出了哪些明确要求？
purpose: 为最终结论中的“是否需要披露机制”提供监管依据
scope: 仅关注美国联邦与州层面的正式法规、监管指引和执法动态；不包含纯评论文章
search_strategy: 优先查找政府官网、监管机构公告、正式法案文本，其次补充高可信媒体解读；检索关键词包含 AI disclosure、generative AI regulation、FTC AI guidance
```

### 子代理返回格式要求

子代理返回结果时，优先贴近 [`agent-result.json`](practice/multi-agent-research-system/schemas/agent-result.json:1) 的核心结构。至少显式包含：

- `agent`
- `status`
- `purpose`
- `scope`
- `queries`
- `sources`
- `findings`
- `gaps`
- `errors`

关键要求：

- `status` 必须明确区分 `ok`、`partial`、`error`、`empty`
- `queries` 必须记录实际执行过的检索词
- `sources` 必须记录来源、来源类型和获取状态
- `findings` 必须记录结论、来源 URL、证据摘录和置信度
- 范围内查不到的内容进入 `gaps`
- 执行失败、访问受限、结构校验失败等问题进入 `errors`

不要只返回自然语言摘要而省略结构化字段。

## 第三阶段：子代理研究必须以网页证据优先

研究优先使用网页搜索/抓取工具，默认先从公开网页证据入手，而不是先凭记忆作答。

执行要求：

- 优先通过 `web_fetch` 或等效网页抓取能力获取公开资料
- 优先选择官方文档、标准组织、论文页面、厂商技术文档、监管机构公告等高可信来源
- 只有在网页证据不足时，才说明证据局限，不要把未经验证的常识当成事实写入结论
- 研究过程中应尽量交叉验证，避免单一来源决定结论

如果没有搜索结果或证据明显不足，必须明确写：**"未找到足够证据"**，不要伪造结论，也不要用猜测填空。

### 证据记录要求

每条发现都必须带完整来源信息，至少包含：

- 发现内容
- 来源 URL
- 证据摘录
- 置信度
- 对应 agent

推荐记录格式（贴近 [`agent-result.json`](practice/multi-agent-research-system/schemas/agent-result.json:42) 中 `findings` 的字段）：

```text
- id: F-001
  summary: OpenAI 在某版本文档中要求工具调用结果以结构化形式返回
  sourceUrl: https://example.com/spec
  evidence: "Tool results should be returned as structured JSON objects..."
  confidence: high
  agent: official-docs
```

如果一个结论来自多个来源，应尽量列出多个来源，并标明哪些来源是直接证据、哪些来源是辅助说明。

### 冲突处理规则

当不同来源之间出现冲突，不要擅自抹平差异，也不要只保留更符合预期的一方。

必须这样处理：

1. 明确标记该问题存在冲突
2. 保留双方或多方证据
3. 把冲突内容写入 `conflicting_findings`
4. 冲突原因的分析（时间差异、口径不同、适用范围不同、证据等级不同等）应写入 `executive_summary` 或 `open_questions`，而不是 `conflicting_findings` 内部

### 冲突记录示例

冲突结果优先贴近 [`final-report.json`](practice/multi-agent-research-system/schemas/final-report.json:32) 的结构：

```text
conflicting_findings:
  - topic: 某模型是否支持函数调用并行执行
    sides:
      - agent: official-docs
        claim: 官方文档称默认支持并行工具调用
        sourceUrl: https://vendor-a.example/doc
      - agent: changelog-review
        claim: 更新日志显示并行执行只在部分套餐可用
        sourceUrl: https://vendor-a.example/changelog
```

## 失败传播与综合前检查

在进入最终综合前，必须读取 [`runtime/failures.json`](practice/multi-agent-research-system/runtime/failures.json:1) 中的失败上下文，并完成以下检查：

- 哪些子代理执行失败
- 失败发生在哪个研究环节
- 失败是否会影响关键结论成立
- 是否需要降低结论置信度
- 是否需要把某部分标记为“未找到足够证据”

如果失败上下文表明某个关键方向没有成功完成检索，综合时必须显式说明证据缺口，不能把缺失部分伪装成“问题不存在”。

### 失败上下文降级规则

如果 [`runtime/failures.json`](practice/multi-agent-research-system/runtime/failures.json:1) 不存在、为空或无法解析：

- 不要默认“没有失败”
- 要在最终输出中显式说明“失败上下文不可用”
- 把这视为证据完整性限制，而不是成功信号
- 当关键方向本来依赖失败上下文判断时，优先降低结论置信度，必要时使用 `insufficient_evidence`

## 第四阶段：最终综合输出

综合阶段的目标不是简单拼接子代理内容，而是形成一份有证据支撑、能反映不确定性的研究结论。

综合时必须做到：

- 先整合高置信度一致结论，再处理争议点
- 对每个核心判断都回溯到对应来源和证据摘录
- 明确区分“已证实”“存在冲突”“未找到足够证据”三种状态
- 如果失败上下文影响了完整性，要在结论中体现范围限制
- 输出要让后续读者能看出：这个结论是如何被拆解、验证、冲突处理并最终形成的

### 最终输出模板

最终报告优先贴近 [`final-report.json`](practice/multi-agent-research-system/schemas/final-report.json:1) 的结构。至少显式包含：

- `question`
- `active_agents`
- `executive_summary`
- `confirmed_findings`
- `conflicting_findings`
- `open_questions`
- `failed_agents`
- `empty_agents`
- `recommendation`
- `coverage`

其中要特别注意：

- `active_agents`：列出本次规划并执行的全部 agent ID
- `confirmed_findings`：每条至少包含 `id`、`summary`、`sourceUrl`、`confidence`、`agent`
- `conflicting_findings`：使用 `topic + sides[]` 结构，而不是自由发挥格式
- `failed_agents`：只记录真正失败的 agent
- `empty_agents`：只记录执行完成但没有找到结果的 agent，不能与失败混淆
- `coverage`：汇总每个 agent 的状态，例如 `ok`、`partial`、`error`、`empty`

### 最终综合示例

```text
question: 某模型 API 是否适合企业内平台接入
active_agents:
  - official-docs
  - integration-review
  - compliance-review
executive_summary: 目前可以确认该 API 具备基础接入能力，但在企业合规披露与部分高级功能可用范围上仍存在证据缺口与来源冲突，因此更适合先做试点而不是直接全面接入。
confirmed_findings:
  - id: F-001
    summary: 官方文档确认支持结构化工具调用
    sourceUrl: https://example.com/docs
    confidence: high
    agent: official-docs
conflicting_findings:
  - topic: 并行工具调用是否默认可用
    sides:
      - agent: official-docs
        claim: 官方文档称默认支持
        sourceUrl: https://example.com/docs
      - agent: integration-review
        claim: 更新日志显示仅部分套餐可用
        sourceUrl: https://example.com/changelog
open_questions:
  - 企业合规披露要求是否覆盖所有目标区域
failed_agents:
  - agent: compliance-review
    errorCategory: access
    message: 监管站点访问受限
    missingScope:
      - 欧盟监管细则
empty_agents: []
recommendation:
  decision: pilot
  rationale:
    - 已确认基础接入能力存在
    - 高级能力边界仍有冲突
    - 合规覆盖尚不完整
coverage:
  - agent: official-docs
    status: ok
    findingCount: 3
  - agent: integration-review
    status: partial
    findingCount: 2
  - agent: compliance-review
    status: error
    findingCount: 0
```

### recommendation 决策规则

`recommendation.decision` 优先使用 [`final-report.json`](practice/multi-agent-research-system/schemas/final-report.json:91) 中约定的枚举值：

- `adopt`
- `pilot`
- `defer`
- `reject`
- `insufficient_evidence`

当出现以下情况时，优先考虑 `insufficient_evidence`：
- 关键 agent 失败
- 失败上下文不可用
- 证据覆盖率过低
- 核心结论存在冲突且无法裁决
- 关键问题仍停留在 `open_questions`

## 输出原则

- 语言清晰，优先写可执行、可核查的内容
- 不要把推测写成事实
- 不要隐去失败、冲突或证据不足
- 不要假设子代理自动共享记忆或上下文
- 所有关键发现都应可追溯到 URL 和证据摘录
- skill 负责行为约束与决策原则，schema 负责结构合同；二者必须显式挂钩

如果证据不足，就明确写“未找到足够证据”；如果证据冲突，就进入 `conflicting_findings`；如果子代理失败影响结论，就在综合中体现失败传播带来的限制。
