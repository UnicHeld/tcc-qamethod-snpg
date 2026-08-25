import json
import re
import sys

DANGEROUS_PATTERNS = [
    r"\brm\s+-rf\b",
    r"git\s+push\s+[^\n]*--force",
    r"git\s+reset\s+--hard",
    r"git\s+clean\s+-[a-z]*f",
    r"git\s+branch\s+-D\b",
    r"\bDROP\s+TABLE\b",
    r"\bTRUNCATE\s+TABLE\b",
    r">\s*/dev/sd",
]


def main():
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        sys.exit(0)

    command = payload.get("tool_input", {}).get("command", "")
    if any(re.search(pattern, command, re.IGNORECASE) for pattern in DANGEROUS_PATTERNS):
        print(
            json.dumps(
                {
                    "hookSpecificOutput": {
                        "hookEventName": "PreToolUse",
                        "permissionDecision": "ask",
                        "permissionDecisionReason": "Comando potencialmente destrutivo detectado. Confirme antes de executar.",
                    }
                }
            )
        )
    sys.exit(0)


if __name__ == "__main__":
    main()
