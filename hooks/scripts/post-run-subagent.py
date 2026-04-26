"""PostToolUse hook: validates sub-agent result structure and surfaces integrity warnings.

Does NOT block execution (always returns 0). Writes warnings to stderr and stdout
so they are visible in Claude Code logs without terminating the workflow.

Rules:
- status=error  -> errors[] must be non-empty
- status=partial -> errors[] must be present
- status=empty  -> gaps[] must be non-empty
- status=ok     -> every finding must have a non-empty sourceUrl
"""
from __future__ import annotations

import json
import sys


def _warn(message: str) -> None:
    """Print a structured warning to stdout and a plain message to stderr."""
    print(json.dumps({"type": "warning", "message": message}))
    print(f"[post-run-subagent WARNING] {message}", file=sys.stderr)


def validate_result(result: dict) -> list[str]:
    warnings: list[str] = []
    status = result.get("status", "")
    agent = result.get("agent", "<unknown>")
    errors = result.get("errors") or []
    gaps = result.get("gaps") or []
    findings = result.get("findings") or []

    if status == "error":
        if not errors:
            warnings.append(
                f"[{agent}] status=error but 'errors' field is empty or missing. "
                "Failure context will be lost without error details."
            )
    elif status == "partial":
        if not errors:
            warnings.append(
                f"[{agent}] status=partial but 'errors' field is empty or absent. "
                "Partial failure context is required for orchestrator synthesis."
            )
    elif status == "empty":
        if not gaps:
            warnings.append(
                f"[{agent}] status=empty but 'gaps' field is empty or missing. "
                "Empty results must document what was searched but not found."
            )
    elif status == "ok":
        missing_urls = [
            f.get("id", "?") for f in findings if not f.get("sourceUrl")
        ]
        if missing_urls:
            warnings.append(
                f"[{agent}] status=ok but findings {missing_urls} are missing 'sourceUrl'. "
                "Every finding must be traceable to a source."
            )

    return warnings


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
        # Response might be a string or None; skip validation
        return 0

    warnings = validate_result(tool_response)
    for w in warnings:
        _warn(w)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
