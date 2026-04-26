"""PreToolUse hook: validates that sub-agent input contains required context fields.

Checks for: question, scope, purpose, search_strategy.
Denies execution if any required field is missing to prevent low-quality research.
"""
from __future__ import annotations

import json
import sys

REQUIRED_FIELDS = ["question", "scope", "purpose", "search_strategy"]


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except json.JSONDecodeError:
        # Non-JSON payload: allow and let the agent handle it
        print(json.dumps({"decision": "allow", "reason": "non-json payload, skipping validation"}))
        return 0

    tool_name = payload.get("tool_name") or payload.get("toolName", "")
    tool_input = payload.get("tool_input") or payload.get("toolInput") or {}

    # Only validate Task/Agent tool calls
    if not any(kw in tool_name.lower() for kw in ("task", "agent")):
        print(json.dumps({"decision": "allow", "reason": f"tool '{tool_name}' is not a sub-agent call"}))
        return 0

    missing = [f for f in REQUIRED_FIELDS if not tool_input.get(f)]
    if missing:
        reason = (
            f"Sub-agent input is missing required context fields: {missing}. "
            "Provide question, scope, purpose, and search_strategy before dispatching a sub-agent."
        )
        print(json.dumps({"decision": "deny", "reason": reason}))
        return 2

    print(json.dumps({"decision": "allow", "reason": "all required context fields present"}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
