import json
import shutil
import subprocess
import sys


def main():
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        sys.exit(0)

    file_path = payload.get("tool_input", {}).get("file_path", "")
    if not file_path.endswith(".py"):
        sys.exit(0)

    ruff = shutil.which("ruff")
    if not ruff:
        sys.exit(0)

    try:
        result = subprocess.run(
            [ruff, "check", file_path],
            capture_output=True,
            text=True,
            timeout=10,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        sys.exit(0)

    if result.returncode != 0:
        print(result.stdout + result.stderr)
    sys.exit(0)


if __name__ == "__main__":
    main()
