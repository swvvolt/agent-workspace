#!/usr/bin/env python3
"""Firecrawl MCP helper for carrier tracking extraction.

Requires FIRECRAWL_API_KEY. Uses only Python standard library.
Connects to Firecrawl remote Streamable HTTP MCP endpoint.
"""
from __future__ import annotations

import argparse
import json
import os
import time
import urllib.request
import uuid
from typing import Any


def mcp_url() -> str:
    key = os.environ.get("FIRECRAWL_API_KEY")
    if not key:
        raise SystemExit("FIRECRAWL_API_KEY is not set. Set it as a secret/env var before using this skill.")
    return f"https://mcp.firecrawl.dev/{key}/v2/mcp"


def rpc(method: str, params: dict[str, Any] | None = None, timeout: int = 60) -> dict[str, Any]:
    payload = {"jsonrpc": "2.0", "id": str(uuid.uuid4()), "method": method, "params": params or {}}
    req = urllib.request.Request(
        mcp_url(),
        data=json.dumps(payload).encode("utf-8"),
        method="POST",
        headers={"Content-Type": "application/json", "Accept": "application/json, text/event-stream"},
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        text = resp.read().decode("utf-8", errors="replace")
    if text.lstrip().startswith("event:") or "data:" in text[:200]:
        for line in text.splitlines():
            if line.startswith("data:"):
                data = line[5:].strip()
                if data and data != "[DONE]":
                    return json.loads(data)
        raise SystemExit("No JSON data event returned from MCP server")
    return json.loads(text)


def call_tool(name: str, arguments: dict[str, Any], timeout: int = 120) -> Any:
    response = rpc("tools/call", {"name": name, "arguments": arguments}, timeout=timeout)
    if "error" in response:
        return {"ok": False, "error": response["error"]}
    return response.get("result", response)


def schema() -> dict[str, Any]:
    return {
        "type": "object",
        "properties": {
            "carrier": {"type": "string"},
            "tracking_number": {"type": "string"},
            "status": {"type": "string"},
            "eta": {"type": ["string", "null"], "description": "ISO date YYYY-MM-DD if visible"},
            "eta_text": {"type": ["string", "null"]},
            "current_location": {"type": ["string", "null"]},
            "last_event": {"type": ["string", "null"]},
            "delivered_at": {"type": ["string", "null"]},
            "signed_by": {"type": ["string", "null"]},
            "source_url": {"type": "string"},
            "confidence": {"type": "string", "enum": ["high", "medium", "low"]},
            "notes": {"type": ["string", "null"]},
        },
        "required": ["carrier", "tracking_number", "status", "source_url", "confidence"],
    }


def print_json(value: Any) -> None:
    print(json.dumps(value, indent=2, ensure_ascii=False))


def cmd_list_tools(args: argparse.Namespace) -> None:
    print_json(rpc("tools/list", timeout=args.timeout))


def cmd_scrape(args: argparse.Namespace) -> None:
    prompt = "Extract carrier tracking information from this rendered carrier page. Return ETA/estimated delivery/estimated arrival if visible. Do not infer delivery from label creation, Odoo status, or warehouse workflow. If ETA is not visible, set eta to null and explain in notes."
    print_json(
        call_tool(
            "firecrawl_scrape",
            {
                "url": args.url,
                "formats": ["json", "markdown"],
                "onlyMainContent": False,
                "waitFor": args.wait_for,
                "jsonOptions": {"prompt": prompt, "schema": schema()},
            },
            timeout=args.timeout,
        )
    )


def cmd_extract(args: argparse.Namespace) -> None:
    prompt = "Extract carrier tracking information. Return ETA/estimated delivery/estimated arrival if visible. Do not infer delivery from label creation or warehouse workflow. If ETA is not visible, set eta to null and explain in notes."
    print_json(call_tool("firecrawl_extract", {"urls": [args.url], "prompt": prompt, "schema": schema(), "enableWebSearch": False, "allowExternalLinks": False}, timeout=args.timeout))


def cmd_agent(args: argparse.Namespace) -> None:
    result = call_tool("firecrawl_agent", {"urls": [args.url], "prompt": "Open this carrier tracking page and extract current tracking status, estimated delivery/arrival date, current location, last event, delivered date/proof, and signer if delivered. Return structured data matching the schema.", "schema": schema()}, timeout=args.timeout)
    print_json({"submitted": result})
    job_id = None
    if isinstance(result, dict):
        job_id = result.get("id") or result.get("jobId") or result.get("job_id")
        content = result.get("content")
        if not job_id and isinstance(content, list):
            for item in content:
                val = item.get("text") if isinstance(item, dict) else None
                if isinstance(val, dict):
                    job_id = val.get("id") or val.get("jobId") or val.get("job_id")
                elif isinstance(val, str):
                    try:
                        parsed = json.loads(val)
                        job_id = parsed.get("id") or parsed.get("jobId") or parsed.get("job_id")
                    except Exception:
                        pass
                if job_id:
                    break
    if not job_id:
        return
    for _ in range(args.polls):
        time.sleep(args.poll_interval)
        status = call_tool("firecrawl_agent_status", {"id": job_id}, timeout=args.timeout)
        print_json({"poll": status})
        lowered = json.dumps(status).lower()
        if "completed" in lowered or "failed" in lowered:
            break


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Use Firecrawl MCP for carrier tracking extraction")
    parser.add_argument("--timeout", type=int, default=120)
    sub = parser.add_subparsers(dest="command", required=True)
    lt = sub.add_parser("list-tools")
    lt.set_defaults(func=cmd_list_tools)
    sc = sub.add_parser("scrape")
    sc.add_argument("url")
    sc.add_argument("--wait-for", type=int, default=5000)
    sc.set_defaults(func=cmd_scrape)
    ex = sub.add_parser("extract")
    ex.add_argument("url")
    ex.set_defaults(func=cmd_extract)
    ag = sub.add_parser("agent")
    ag.add_argument("url")
    ag.add_argument("--polls", type=int, default=8)
    ag.add_argument("--poll-interval", type=int, default=15)
    ag.set_defaults(func=cmd_agent)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
