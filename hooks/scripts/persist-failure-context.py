"""PostToolUse hook: persists sub-agent failure context to runtime/failures.json.

Activates when a sub-agent result has status=error or status=partial with errors.
Appends a structured failure record to runtime/failures.json (one JSON object per line).
The orchestrator MUST read this file before producing the final report.
"""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path


def extract_failure_record(result: dict) -> dict | None:
    """Return a failure record dict if the result warrants persistence, else None."""
    status = result.get("status", "")
    errors = result.get("errors") or []

    if status == "error" or (status == "partial" and errors):
        first_error = errors[0] if errors else {}
        return {
            "agent": result.get("agent", "<unknown>"),
            "errorCategory": first_error.get("errorCategory", "unknown"),
            "message": first_error.get("message", "No error message provided."),
            "failedSources": first_error.get("failedSources", []),
            "partialFindings": result.get("findings") or [],
            "missingScope": result.get("gaps") or [],
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    return None


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except json.JSONDecodeError:
        return 0

    tool_name = payload.get("tool_name") or payload.get("toolName", "")
    if not any(kw in tool_name.lower() for kw in ("task", "agent")):
        return 0

    tool_response = payload.get("tool_response") or payload.get("toolResponse")
    if not isinstance(tool_response, dict):
        return 0

    record = extract_failure_record(tool_response)
    if record is None:
        return 0

    plugin_root = os.environ.get("CLAUDE_PLUGIN_ROOT")
    if not plugin_root:
        print(
            json.dumps({"warning": "CLAUDE_PLUGIN_ROOT not set; failure context not persisted."})
        )
        return 0

    failures_file = Path(plugin_root) / "runtime" / "failures.json"
    failures_file.parent.mkdir(parents=True, exist_ok=True)

    # Read existing records
    existing: list = []
    if failures_file.exists() and failures_file.stat().st_size > 0:
        try:
            existing = json.loads(failures_file.read_text(encoding="utf-8"))
            if not isinstance(existing, list):
                existing = []
        except (json.JSONDecodeError, OSError):
            existing = []

    existing.append(record)
    failures_file.write_text(json.dumps(existing, ensure_ascii=False, indent=2), encoding="utf-8")

    print(
        json.dumps({
            "type": "info",
            "message": f"Failure context for agent '{record['agent']}' persisted to {failures_file}.",
        })
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
