# Multi-Agent Research System

[English README](README.md) | [中文说明](README_CN.md)

这是一个基于 Claude Code plugin 的通用多代理研究系统，聚焦开放式研究任务的拆解、执行、失败传播与最终综合。项目强调：动态规划研究角色、显式传递上下文、基于真实网页证据开展研究，以及在结果中保留失败、空结果与冲突信息。

## 项目概览

该项目用于构建一个更可信的研究工作流，而不是只追求“总能给出答案”。系统核心由以下部分组成：

- **协调者 / Skill**：根据研究目标与约束，动态规划子代理角色与任务边界。
- **Hooks**：在子代理执行前后做上下文校验、结果校验与失败信息持久化。
- **Schemas**：约束研究任务、子代理结果和最终综合报告的数据结构。
- **Runtime 状态**：记录失败上下文，供最终综合阶段读取。
- **测试用例**：覆盖动态角色规划、空结果处理、失败传播、冲突保留等关键行为。

## 核心能力

- **动态角色规划**：根据具体研究问题动态决定子代理数量与职责，而不是套用固定模板。
- **显式上下文传递**：子代理任务包含明确的 `question`、`purpose`、`scope`、`search_strategy` 等字段。
- **网页证据优先**：优先基于真实网页搜索与抓取结果形成结论，而不是依赖本地样例或主观记忆。
- **结构化失败传播**：对子代理失败、部分成功、空结果进行区分，并将失败上下文向上游暴露。
- **冲突保留与证据边界表达**：不同来源冲突时不强行合并，允许最终报告给出 `insufficient_evidence`。

## 目录结构

```text
metasearch/
├── README.md
├── README_CN.md
├── requirements.txt
├── .claude-plugin/
├── hooks/
│   ├── hooks.json
│   └── scripts/
│       ├── pre-run-subagent.py
│       ├── post-run-subagent.py
│       └── persist-failure-context.py
├── runtime/
│   └── failures.json
├── schemas/
│   ├── research-brief.json
│   ├── agent-result.json
│   └── final-report.json
├── skills/
│   └── research-orchestrator/
│       └── SKILL.md
└── test/
    ├── acceptance.md
    ├── functional_test.py
    └── test_hooks.py
```

## 关键文件说明

- [`.claude-plugin/`](.claude-plugin:1)：Claude Code plugin 配置目录。
- [`hooks/hooks.json`](hooks/hooks.json:1)：定义子代理执行前后触发的 Hook。
- [`hooks/scripts/pre-run-subagent.py`](hooks/scripts/pre-run-subagent.py:1)：执行前校验子代理输入上下文是否完整。
- [`hooks/scripts/post-run-subagent.py`](hooks/scripts/post-run-subagent.py:1)：执行后检查结果结构与状态。
- [`hooks/scripts/persist-failure-context.py`](hooks/scripts/persist-failure-context.py:1)：将失败上下文写入运行时文件。
- [`runtime/failures.json`](runtime/failures.json:1)：持久化失败信息，供最终综合时读取。
- [`schemas/research-brief.json`](schemas/research-brief.json:1)：研究任务输入结构定义。
- [`schemas/agent-result.json`](schemas/agent-result.json:1)：子代理结构化输出定义。
- [`schemas/final-report.json`](schemas/final-report.json:1)：最终综合报告结构定义。
- [`skills/research-orchestrator/SKILL.md`](skills/research-orchestrator/SKILL.md:1)：多代理研究协调流程说明。
- [`test/acceptance.md`](test/acceptance.md:1)：人工验收场景与通过标准。
- [`test/test_hooks.py`](test/test_hooks.py:1)、[`test/functional_test.py`](test/functional_test.py:1)：Hook 与系统行为测试。

## 工作流程

1. **定义研究问题**  
   输入研究问题、决策目标以及约束条件，例如来源类型、时间范围、区域限制等。

2. **规划子代理角色**  
   协调者基于研究目标生成若干边界清晰的子代理，并为每个角色指定职责范围与检索策略。

3. **执行研究任务**  
   子代理依据显式上下文开展网页研究，记录实际查询、来源、发现、缺口和错误。

4. **校验并持久化失败信息**  
   Hook 在执行前后进行校验，并将失败、部分成功或异常上下文写入运行时文件。

5. **综合最终报告**  
   协调者聚合研究结果、冲突信息和失败上下文，生成带证据边界的最终报告。

## 数据结构

### 1. Research Brief

[`schemas/research-brief.json`](schemas/research-brief.json:1) 定义研究任务输入，核心字段包括：

- `question`
- `decision_goal`
- `constraints`
- `planned_agents`

### 2. Agent Result

[`schemas/agent-result.json`](schemas/agent-result.json:1) 定义单个子代理输出，重点字段包括：

- `status`：`ok` / `partial` / `error` / `empty`
- `queries`
- `sources`
- `findings`
- `gaps`
- `errors`

### 3. Final Report

[`schemas/final-report.json`](schemas/final-report.json:1) 定义最终综合输出，重点字段包括：

- `confirmed_findings`
- `conflicting_findings`
- `open_questions`
- `failed_agents`
- `empty_agents`
- `recommendation`
- `coverage`

## 关键约束

- **无证据不补结论**：没有足够公开证据时，应明确返回证据不足，而不是生成推测性结论。
- **空结果与失败分离**：`empty` 表示未找到结果，`error` 表示执行失败，两者不可混用。
- **失败需要向上游传播**：失败上下文必须进入 [`runtime/failures.json`](runtime/failures.json:1)，并在最终综合中体现。
- **冲突信息必须保留**：不同来源不一致时，必须进入 `conflicting_findings`，不得被静默覆盖。
- **允许不确定结论**：最终建议可返回 `insufficient_evidence`，以真实表达证据边界。

## 测试与验收

### 自动化测试

安装测试依赖并运行：

```bash
python3 -m pip install -r requirements.txt
python3 -m pytest ./test/test_hooks.py ./test/functional_test.py -v
```

- [`test/acceptance.md`](test/acceptance.md:1)：用于人工验收，覆盖单角色、多角色、无搜索结果、抓取失败、来源冲突、失败传播等场景。
- [`test/test_hooks.py`](test/test_hooks.py:1)：用于验证 Hook 前后置行为与失败持久化逻辑。
- [`test/functional_test.py`](test/functional_test.py:1)：用于验证关键功能路径，现已同时兼容 pytest 收集与脚本直接执行。

## 运行环境

- **运行项目本体**：Python 3.11+ 标准库
- **运行测试**：`pytest>=8.0`

[`requirements.txt`](requirements.txt:1) 当前用于声明测试依赖；项目本体本身不依赖额外第三方运行时包。
