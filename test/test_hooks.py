import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Optional

import pytest


PLUGIN_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = PLUGIN_ROOT / "hooks" / "scripts"
PRE_RUN_SCRIPT = SCRIPTS_DIR / "pre-run-subagent.py"
POST_RUN_SCRIPT = SCRIPTS_DIR / "post-run-subagent.py"
PERSIST_FAILURE_SCRIPT = SCRIPTS_DIR / "persist-failure-context.py"


def run_hook(script_path: Path, payload: dict, env: Optional[dict] = None) -> subprocess.CompletedProcess[str]:
    merged_env = os.environ.copy()
    if env:
        merged_env.update(env)

    return subprocess.run(
        [sys.executable, str(script_path)],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        env=merged_env,
        check=False,
    )


def test_pre_run_denies_when_question_is_missing() -> None:
    payload = {
        "tool_name": "Task",
        "tool_input": {
            "scope": "只查官方文档",
            "purpose": "验证假设",
            "search_strategy": "先官方后社区",
        },
    }

    result = run_hook(PRE_RUN_SCRIPT, payload)

    assert result.returncode == 2
    response = json.loads(result.stdout)
    assert response["decision"] == "deny"
    assert "question" in response["reason"]


def test_pre_run_allows_when_required_fields_are_present() -> None:
    payload = {
        "tool_name": "Task",
        "tool_input": {
            "question": "Claude Code hooks 如何传递结构化结果？",
            "scope": "仅限项目内约定与官方能力",
            "purpose": "生成可执行研究结论",
            "search_strategy": "先读 schema，再核对 hooks",
        },
    }

    result = run_hook(PRE_RUN_SCRIPT, payload)

    assert result.returncode == 0
    response = json.loads(result.stdout)
    assert response["decision"] == "allow"
    assert response["reason"] == "all required context fields present"


def test_post_run_warns_when_empty_status_has_no_gaps() -> None:
    payload = {
        "tool_name": "Task",
        "tool_response": {
            "agent": "source-scanner",
            "status": "empty",
            "findings": [],
        },
    }

    result = run_hook(POST_RUN_SCRIPT, payload)

    assert result.returncode == 0
    stdout_lines = [line for line in result.stdout.strip().splitlines() if line]
    assert stdout_lines, "expected a warning JSON line on stdout"

    warning = json.loads(stdout_lines[0])
    assert warning["type"] == "warning"
    assert "status=empty" in warning["message"]
    assert "gaps" in warning["message"]
    assert "status=empty" in result.stderr


def test_persist_failure_context_writes_failures_json_for_error_result(tmp_path: Path) -> None:
    plugin_root = tmp_path / "plugin-root"
    payload = {
        "tool_name": "Task",
        "tool_response": {
            "agent": "web-researcher",
            "status": "error",
            "findings": [{"id": "f-1", "title": "partial clue"}],
            "gaps": ["official pricing page inaccessible"],
            "errors": [
                {
                    "errorCategory": "network",
                    "message": "Request timed out",
                    "failedSources": ["https://example.com/pricing"],
                }
            ],
        },
    }

    result = run_hook(
        PERSIST_FAILURE_SCRIPT,
        payload,
        env={"CLAUDE_PLUGIN_ROOT": str(plugin_root)},
    )

    assert result.returncode == 0
    info = json.loads(result.stdout)
    assert info["type"] == "info"
    assert "persisted" in info["message"]

    failures_file = plugin_root / "runtime" / "failures.json"
    assert failures_file.exists()

    persisted = json.loads(failures_file.read_text(encoding="utf-8"))
    assert isinstance(persisted, list)
    assert len(persisted) == 1

    record = persisted[0]
    assert record["agent"] == "web-researcher"
    assert record["errorCategory"] == "network"
    assert record["message"] == "Request timed out"
    assert record["failedSources"] == ["https://example.com/pricing"]
    assert record["partialFindings"] == [{"id": "f-1", "title": "partial clue"}]
    assert record["missingScope"] == ["official pricing page inaccessible"]
    assert record["timestamp"]
