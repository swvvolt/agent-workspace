"""Windows-safe wrapper for the 17TRACK MCP server.

Requires API_TOKEN_17TRACK in the environment. Does not print the token.
"""
from __future__ import annotations

import json
import os
import pathlib
import subprocess
import sys
import threading
import time


def _candidate_servers() -> list[pathlib.Path]:
    """Return candidate MCP server entrypoints without relying on absolute user paths."""
    configured = os.environ.get("TRACK17_MCP_SERVER")
    candidates: list[pathlib.Path] = []
    if configured:
        candidates.append(pathlib.Path(configured).expanduser())

    script_path = pathlib.Path(__file__).resolve()
    repo_root = script_path.parents[2]
    candidates.append(
        repo_root
        / "extensions"
        / "17track-mcp"
        / "node_modules"
        / "mcp-server-17track"
        / "index.js"
    )

    candidates.append(
        pathlib.Path.home()
        / ".letta"
        / "mcp-servers"
        / "17track"
        / "node_modules"
        / "mcp-server-17track"
        / "index.js"
    )
    return candidates


def _find_server() -> pathlib.Path | None:
    for candidate in _candidate_servers():
        if candidate.exists():
            return candidate
    return None


def _wait_for_response(responses: dict[int, dict], response_id: int, timeout_seconds: float) -> bool:
    deadline = time.time() + timeout_seconds
    while response_id not in responses and time.time() < deadline:
        time.sleep(0.05)
    return response_id in responses


def main() -> int:
    if len(sys.argv) < 2:
        print("Usage: track17.py TRACKING_NUMBER", file=sys.stderr)
        return 2

    tracking = sys.argv[1].strip()
    if not tracking:
        print("Tracking number is empty", file=sys.stderr)
        return 2

    token = os.environ.get("API_TOKEN_17TRACK")
    if not token:
        print("API_TOKEN_17TRACK is not set", file=sys.stderr)
        return 2

    server = _find_server()
    if server is None:
        print(
            "MCP server is not installed. Run: npm install --prefix extensions/17track-mcp",
            file=sys.stderr,
        )
        return 2

    proc = subprocess.Popen(
        ["node", str(server)],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        env=os.environ.copy(),
    )

    responses: dict[int, dict] = {}
    errors: list[str] = []

    def read_stdout() -> None:
        assert proc.stdout is not None
        for line in proc.stdout:
            line = line.strip()
            if not line:
                continue
            try:
                msg = json.loads(line)
                if "id" in msg:
                    responses[int(msg["id"])] = msg
            except Exception as exc:  # pragma: no cover - defensive wrapper logging
                errors.append(f"stdout parse error: {exc}: {line[:200]}")

    def read_stderr() -> None:
        assert proc.stderr is not None
        for line in proc.stderr:
            errors.append(line.rstrip())

    threading.Thread(target=read_stdout, daemon=True).start()
    threading.Thread(target=read_stderr, daemon=True).start()

    def send(message: dict) -> None:
        assert proc.stdin is not None
        proc.stdin.write(json.dumps(message) + "\n")
        proc.stdin.flush()

    try:
        send({"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}})
        if not _wait_for_response(responses, 1, 30):
            print(json.dumps({"ok": False, "error": "timeout listing tools", "stderr": errors}, indent=2))
            return 1

        send(
            {
                "jsonrpc": "2.0",
                "id": 2,
                "method": "tools/call",
                "params": {"name": "track_package", "arguments": {"number": tracking}},
            }
        )
        if not _wait_for_response(responses, 2, 60):
            print(json.dumps({"ok": False, "error": "timeout calling track_package", "stderr": errors}, indent=2))
            return 1

        result = responses[2]
        try:
            text = result["result"]["content"][0]["text"]
            result["parsed_text"] = json.loads(text)
        except Exception:
            pass
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return 0
    finally:
        proc.kill()


if __name__ == "__main__":
    raise SystemExit(main())
