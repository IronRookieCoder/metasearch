"""功能测试：覆盖关键验收场景，并兼容 pytest 与命令行脚本执行。"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Optional


PLUGIN_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = PLUGIN_ROOT / "hooks" / "scripts"
PRE = SCRIPTS / "pre-run-subagent.py"
POST = SCRIPTS / "post-run-subagent.py"
PERSIST = SCRIPTS / "persist-failure-context.py"


def run(script: Path, payload: dict, env_extra: dict | None = None) -> subprocess.CompletedProcess[str]:
    merged = os.environ.copy()
    if env_extra:
        merged.update(env_extra)
    return subprocess.run(
        [sys.executable, str(script)],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        env=merged,
        check=False,
    )


def _run_acceptance_checks() -> list[tuple[str, bool, str]]:
    results: list[tuple[str, bool, str]] = []

    # 场景 1：单角色研究 — 前置校验通过
    res = run(PRE, {
        "tool_name": "Task",
        "tool_input": {
            "question": "LangGraph 是否适合企业工作流编排？",
            "scope": "仅查官方文档与 GitHub 仓库",
            "purpose": "支持技术选型",
            "search_strategy": "先官网后 GitHub README",
        },
    })
    out = json.loads(res.stdout)
    ok = res.returncode == 0 and out["decision"] == "allow"
    results.append(("单角色研究 - 前置校验通过", ok, f"decision={out['decision']}"))

    # 场景 2：多角色研究 — 前置校验通过（含 4 个维度字段）
    res = run(PRE, {
        "tool_name": "Agent",
        "tool_input": {
            "question": "某开源库是否适合企业平台接入？",
            "scope": "官方文档 / 维护风险 / 集成成本 / 合规风险 / 性能基准",
            "purpose": "生成接入决策建议书",
            "search_strategy": "按维度拆分多角色，每个角色仅查其负责的来源类型",
        },
    })
    out = json.loads(res.stdout)
    ok = res.returncode == 0 and out["decision"] == "allow"
    results.append(("多角色研究 - 前置校验通过", ok, f"decision={out['decision']}"))

    # 场景 3：无搜索结果 — status=empty 且 gaps 已填写
    res = run(POST, {
        "tool_name": "Task",
        "tool_response": {
            "agent": "cold-topic-researcher",
            "status": "empty",
            "findings": [],
            "gaps": ["未找到目标主题的任何公开中英文资料"],
        },
    })
    ok = res.returncode == 0 and res.stdout.strip() == ""
    results.append(("无搜索结果 - gaps 完整不触发 warning", ok,
                    f"stdout='{res.stdout.strip()}' stderr='{res.stderr.strip()}'"))

    # 场景 3b：无搜索结果 — status=empty 但缺少 gaps → 应产生 warning
    res = run(POST, {
        "tool_name": "Task",
        "tool_response": {
            "agent": "cold-topic-researcher",
            "status": "empty",
            "findings": [],
        },
    })
    out_lines = [line for line in res.stdout.strip().splitlines() if line]
    ok = res.returncode == 0 and bool(out_lines) and "gaps" in json.loads(out_lines[0])["message"]
    results.append(("无搜索结果 - 缺少 gaps 触发 warning", ok,
                    f"warning={'yes' if out_lines else 'no'}"))

    # 场景 4：网页抓取失败 — 失败上下文落盘
    with tempfile.TemporaryDirectory() as td:
        plugin_root = Path(td)
        res = run(PERSIST, {
            "tool_name": "Task",
            "tool_response": {
                "agent": "official-docs",
                "status": "error",
                "findings": [{"id": "F-001", "summary": "首页可访问但目标页超时"}],
                "gaps": ["pricing page"],
                "errors": [{
                    "errorCategory": "access",
                    "message": "403 fetching pricing page",
                    "failedSources": ["https://example.com/pricing"],
                }],
            },
        }, {"CLAUDE_PLUGIN_ROOT": str(plugin_root)})
        fp = plugin_root / "runtime" / "failures.json"
        data = json.loads(fp.read_text(encoding="utf-8")) if fp.exists() else []
        ok = (res.returncode == 0 and len(data) == 1
              and data[0]["agent"] == "official-docs"
              and data[0]["errorCategory"] == "access")
        results.append(("网页抓取失败 - 失败上下文落盘", ok,
                        f"persisted={len(data)} records, agent={data[0]['agent'] if data else 'N/A'}"))

    # 场景 5：来源冲突 — 后置校验允许双方证据保留（status=ok 且 sourceUrl 齐全）
    res = run(POST, {
        "tool_name": "Task",
        "tool_response": {
            "agent": "comparison-agent",
            "status": "ok",
            "findings": [
                {"id": "F-001", "summary": "官方文档称支持 SSO",
                 "sourceUrl": "https://official.example/sso", "evidence": "docs: SSO supported"},
                {"id": "F-002", "summary": "Issue 中称企业版前不可用",
                 "sourceUrl": "https://github.com/example/issues/1", "evidence": "issue: SSO enterprise only"},
            ],
        },
    })
    ok = res.returncode == 0 and res.stdout.strip() == ""
    results.append(("来源冲突 - 双方证据齐全不触发 warning", ok,
                    f"stdout='{res.stdout.strip()}'"))

    # 场景 6：失败传播 — partial 结果保留 partialFindings
    with tempfile.TemporaryDirectory() as td:
        plugin_root = Path(td)
        res = run(PERSIST, {
            "tool_name": "Task",
            "tool_response": {
                "agent": "maintainer-risk",
                "status": "partial",
                "findings": [{"id": "F-003", "summary": "近 90 天仍有提交",
                              "sourceUrl": "https://github.com/example/repo",
                              "evidence": "recent commits visible"}],
                "gaps": ["release cadence detail missing"],
                "errors": [{
                    "errorCategory": "transient",
                    "message": "Issue list timeout",
                    "failedSources": ["https://github.com/example/repo/issues"],
                }],
            },
        }, {"CLAUDE_PLUGIN_ROOT": str(plugin_root)})
        fp = plugin_root / "runtime" / "failures.json"
        data = json.loads(fp.read_text(encoding="utf-8")) if fp.exists() else []
        ok = (res.returncode == 0 and len(data) == 1
              and data[0]["agent"] == "maintainer-risk"
              and bool(data[0]["partialFindings"]))
        results.append(("失败传播 - partial 结果保留 partialFindings", ok,
                        f"partialFindings count={len(data[0]['partialFindings']) if data else 0}"))

    return results


def print_summary(results: list[tuple[str, bool, str]]) -> int:
    print("\n" + "=" * 60)
    print("功能测试汇总")
    print("=" * 60)
    passed = 0
    for name, ok, detail in results:
        status = "[PASS]" if ok else "[FAIL]"
        print(f"  {status}  {name}")
        print(f"           {detail}")
        if ok:
            passed += 1
    print("=" * 60)
    print(f"结果：{passed}/{len(results)} 通过")
    print("=" * 60)
    return passed


def test_acceptance_scenarios_all_pass() -> None:
    results = _run_acceptance_checks()
    failed = [name for name, ok, _ in results if not ok]
    assert not failed, f"以下功能场景未通过: {failed}"


if __name__ == "__main__":
    results = _run_acceptance_checks()
    passed = print_summary(results)
    raise SystemExit(0 if passed == len(results) else 1)
