# Multi-Agent Research System

[English](README.md) | [中文说明](README_CN.md)

A general-purpose multi-agent research system built on top of the Claude Code plugin. It focuses on decomposing open-ended research tasks, executing sub-agent research, propagating failure information, and synthesizing traceable final reports.

The core design principle is **trustworthiness over completeness**: the system is designed to express evidence boundaries honestly rather than always producing a confident-sounding answer.

## Overview

The system is composed of the following layers:

| Layer | Description |
|---|---|
| **Orchestrator / Skill** | Dynamically plans sub-agent roles and task boundaries based on the research goal and constraints |
| **Hooks** | Validate sub-agent input/output and persist failure context before and after each execution |
| **Schemas** | Define the structure for research briefs, agent results, and final reports |
| **Runtime state** | Persist failure context so the orchestrator can incorporate it into the final synthesis |
| **Tests** | Cover dynamic role planning, empty result handling, failure propagation, and conflict preservation |

## Key Capabilities

- **Dynamic role planning** — Sub-agent roles and count are determined per task, not from a fixed template.
- **Explicit context passing** — Each sub-agent receives `question`, `purpose`, `scope`, and `search_strategy` explicitly; no implicit context sharing.
- **Web-first evidence** — Research is grounded in real web search and page retrieval, not local mock data.
- **Structured failure propagation** — Failure, partial success, and empty results are distinguished and surfaced upstream.
- **Conflict preservation** — Contradictions between sources are preserved in `conflicting_findings`; the final report may return `insufficient_evidence`.

## Repository Structure

```text
metasearch/
├── README.md                            # This file (English)
├── README_CN.md                         # Chinese version
├── requirements.txt
├── .claude-plugin/                      # Claude Code plugin manifest
├── hooks/
│   ├── hooks.json                       # Hook configuration
│   └── scripts/
│       ├── pre-run-subagent.py          # Validates sub-agent input context
│       ├── post-run-subagent.py         # Validates sub-agent output structure
│       └── persist-failure-context.py   # Persists failure context to runtime
├── runtime/
│   └── failures.json                    # Runtime failure log
├── schemas/
│   ├── research-brief.json              # Input schema for a research task
│   ├── agent-result.json                # Sub-agent output schema
│   └── final-report.json                # Final synthesized report schema
├── skills/
│   └── research-orchestrator/
│       └── SKILL.md                     # Orchestrator workflow definition
└── test/
    ├── acceptance.md                    # Manual acceptance scenarios
    ├── functional_test.py
    └── test_hooks.py
```

## Workflow

### Step 1 — Define the research brief

Provide a research question, decision goal, and constraints (e.g. allowed source types, time range, region):

```json
{
  "question": "Does service X meet enterprise compliance requirements?",
  "decision_goal": "Decide whether to integrate X into our internal platform.",
  "constraints": {
    "allowed_source_types": ["official", "policy", "pricing"],
    "time_range": "2024-01-01/2025-12-31",
    "region": "CN"
  },
  "planned_agents": [...]
}
```

### Step 2 — Orchestrator plans sub-agent roles

The orchestrator reads the brief and generates a set of non-overlapping sub-agent roles, each with a distinct `scope` and `search_strategy`.

### Step 3 — Sub-agents execute web research

Each sub-agent receives its full task context explicitly and performs real web searches. It records:

- Actual queries executed
- Sources retrieved (with retrieval status)
- Structured findings (with source URL, evidence quote, confidence)
- Gaps within scope that could not be found
- Errors (timeout, access blocked, validation failure)

### Step 4 — Hooks validate and persist failure context

`pre-run-subagent.py` checks that required context fields are present before execution.  
`post-run-subagent.py` checks that the result structure is valid after execution.  
`persist-failure-context.py` writes failure summaries to [`runtime/failures.json`](runtime/failures.json:1).

### Step 5 — Orchestrator synthesizes the final report

The orchestrator reads all agent results and the failure log, then produces a final report that explicitly includes:

- `confirmed_findings` — findings backed by retrievable evidence
- `conflicting_findings` — contradictions between sources, preserved as-is
- `open_questions` — questions raised but not resolved
- `failed_agents` — agents that errored, with affected scope
- `empty_agents` — agents that returned no results
- `recommendation` — one of `adopt / pilot / defer / reject / insufficient_evidence`
- `coverage` — an assessment of how well the research covered the question

## Data Schemas

### Research Brief — [`schemas/research-brief.json`](schemas/research-brief.json:1)

| Field | Required | Description |
|---|---|---|
| `question` | ✓ | The research question |
| `decision_goal` | ✓ | The decision this research supports |
| `constraints` | ✓ | Source types, time range, region |
| `planned_agents` | ✓ | Array of agent definitions (agent, purpose, scope, search_strategy) |

### Agent Result — [`schemas/agent-result.json`](schemas/agent-result.json:1)

| Field | Required | Description |
|---|---|---|
| `agent` | ✓ | Agent identifier |
| `status` | ✓ | `ok` / `partial` / `error` / `empty` |
| `queries` | ✓ | Search queries actually executed |
| `sources` | ✓ | Retrieved sources with type and retrieval status |
| `findings` | ✓ | Structured findings with evidence and confidence |
| `gaps` | ✓ | Topics within scope that could not be found |
| `errors` | ✓ | Structured error entries when status is `error` |

### Final Report — [`schemas/final-report.json`](schemas/final-report.json:1)

| Field | Required | Description |
|---|---|---|
| `confirmed_findings` | ✓ | Cross-agent confirmed findings |
| `conflicting_findings` | ✓ | Contradictions preserved without forced resolution |
| `open_questions` | ✓ | Unresolved questions |
| `failed_agents` | ✓ | Agents that failed, with missing scope |
| `empty_agents` | ✓ | Agents that returned no results |
| `recommendation.decision` | ✓ | `adopt / pilot / defer / reject / insufficient_evidence` |
| `coverage` | ✓ | Evidence coverage assessment |

## Operating Constraints

1. **No mock fallback** — If no evidence is found, the system must return an empty or insufficient-evidence result, not fabricated content.
2. **Empty ≠ Error** — `empty` means no results were found; `error` means execution failed. These must not be conflated.
3. **Failure must propagate** — Failure context is persisted to [`runtime/failures.json`](runtime/failures.json:1) and must be reflected in the final report.
4. **Conflicts must be preserved** — When sources disagree, both sides enter `conflicting_findings`; the system must not silently resolve them.
5. **Uncertainty is a valid output** — `insufficient_evidence` is an explicit and acceptable recommendation when coverage is too low.

## Testing & Acceptance

### Automated tests

Install test dependencies and run:

```bash
python3 -m pip install -r requirements.txt
python3 -m pytest ./test/test_hooks.py ./test/functional_test.py -v
```

- [`test/test_hooks.py`](test/test_hooks.py:1) — Tests pre/post hook behavior and failure persistence.
- [`test/functional_test.py`](test/functional_test.py:1) — Tests end-to-end system behavior across key scenarios; it now supports both pytest collection and direct script execution.

### Manual acceptance

[`test/acceptance.md`](test/acceptance.md:1) defines 8 acceptance scenarios covering:

| ID | Scenario |
|---|---|
| AC-01 | Single-agent research with only official sources |
| AC-02 | Multi-agent research for an integration decision |
| AC-03 | No search results — insufficient public evidence |
| AC-04 | Page retrieval failure — source found but content unavailable |
| AC-05 | Conflicting sources — different claims about the same feature |
| AC-06 | Failure propagation — a sub-agent failure must appear in the final report |
| AC-07 | Mixed outcome — one agent succeeds, one is empty, one fails |
| AC-08 | Role boundary — sub-agents must not duplicate research coverage |

The acceptance bar requires at least 6 of 8 scenarios to pass, covering all major failure modes.

## Requirements

- **Runtime**: Python 3.11+ standard library for the project implementation
- **Testing**: `pytest>=8.0`

See [`requirements.txt`](requirements.txt:1) for the declared test dependency.
