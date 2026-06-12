#!/usr/bin/env python3
"""17TRACK v2.4 tracking wrapper using register + gettrackinfo.

Requires API_TOKEN_17TRACK in environment. Does not print the token.

This intentionally avoids mcp-server-17track's getRealTimeTrackInfo endpoint,
because Verivolt's current 17TRACK token is not authorized for that separately
gated interface. The standard register + gettrackinfo workflow works.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request
from typing import Any


try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass


API_BASE = "https://api.17track.net/track/v2.4"

# Known useful carrier codes. 17TRACK carrier code 100003 returned FedEx data
# for Verivolt test tracking number 872922612240. 100002 is UPS.
DEFAULT_CARRIER_CODES = {
    "fedex": 100003,
    "fedex-fdx": 100003,
    "fdx": 100003,
    "ups": 100002,
}


def post(endpoint: str, payload: list[dict[str, Any]], token: str) -> dict[str, Any]:
    req = urllib.request.Request(
        f"{API_BASE}/{endpoint}",
        data=json.dumps(payload).encode("utf-8"),
        method="POST",
        headers={
            "17token": token,
            "Content-Type": "application/json",
            "client-id": "diana-17track-wrapper",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        try:
            parsed = json.loads(body)
        except Exception:
            parsed = {"body": body}
        return {"code": exc.code, "http_error": True, "data": parsed}


def normalize_status(status: str | None, sub_status: str | None) -> str:
    text = f"{status or ''} {sub_status or ''}".lower()
    if "delivered" in text:
        return "delivered"
    if "exception" in text or "alert" in text or "fail" in text:
        return "exception"
    if "pickup" in text or "transit" in text or "info" in text:
        return "in_transit"
    if "notfound" in text or "not_found" in text:
        return "not_found"
    if not text.strip():
        return "unknown"
    return status or "unknown"


def extract_summary(number: str, carrier: int | None, query: dict[str, Any], register: dict[str, Any]) -> dict[str, Any]:
    accepted = (query.get("data") or {}).get("accepted") or []
    rejected = (query.get("data") or {}).get("rejected") or []
    if not accepted:
        return {
            "ok": False,
            "number": number,
            "carrier": carrier,
            "status": "unavailable",
            "register_response": register,
            "query_response": query,
            "rejected": rejected,
        }

    item = accepted[0]
    info = item.get("track_info") or {}
    latest_status = info.get("latest_status") or {}
    latest_event = info.get("latest_event") or {}
    time_metrics = info.get("time_metrics") or {}
    eta = time_metrics.get("estimated_delivery_date") or {}
    shipping_info = info.get("shipping_info") or {}

    status = latest_status.get("status")
    sub_status = latest_status.get("sub_status")
    normalized = normalize_status(status, sub_status)

    events: list[dict[str, Any]] = []
    tracking = info.get("tracking") or {}
    for provider in tracking.get("providers") or []:
        provider_info = provider.get("provider") or {}
        for event in provider.get("events") or []:
            events.append(
                {
                    "time_utc": event.get("time_utc"),
                    "time_iso": event.get("time_iso"),
                    "description": event.get("description"),
                    "location": event.get("location"),
                    "sub_status": event.get("sub_status"),
                    "provider": provider_info.get("name"),
                }
            )

    delivered_at = None
    if normalized == "delivered":
        delivered_at = latest_event.get("time_utc") or latest_event.get("time_iso")

    return {
        "ok": True,
        "number": item.get("number", number),
        "carrier": item.get("carrier", carrier),
        "status": normalized,
        "status_raw": status,
        "sub_status": sub_status,
        "latest_event": {
            "time_utc": latest_event.get("time_utc"),
            "time_iso": latest_event.get("time_iso"),
            "description": latest_event.get("description"),
            "location": latest_event.get("location"),
            "sub_status": latest_event.get("sub_status"),
        }
        if latest_event
        else None,
        "eta": eta.get("from"),
        "eta_to": eta.get("to"),
        "eta_source": eta.get("source"),
        "delivered_at": delivered_at,
        "origin": (shipping_info.get("shipper_address") or {}),
        "destination": (shipping_info.get("recipient_address") or {}),
        "time_metrics": time_metrics,
        "events": events,
        "register_response": register,
        "query_response": query,
    }


def carrier_payload(number: str, carrier: str | int | None) -> dict[str, Any]:
    payload: dict[str, Any] = {"number": number}
    if carrier is None:
        return payload
    if isinstance(carrier, int):
        payload["carrier"] = carrier
        return payload
    carrier_text = str(carrier).strip()
    if not carrier_text:
        return payload
    if carrier_text.isdigit():
        payload["carrier"] = int(carrier_text)
    else:
        payload["carrier"] = DEFAULT_CARRIER_CODES.get(carrier_text.lower(), carrier_text)
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(description="Track a package with 17TRACK v2.4 register + gettrackinfo")
    parser.add_argument("number", help="tracking number")
    parser.add_argument("--carrier", help="17TRACK carrier code or alias, e.g. fedex or 100003", default="fedex")
    parser.add_argument("--no-register", action="store_true", help="skip register and only query gettrackinfo")
    parser.add_argument("--raw", action="store_true", help="output raw register/query responses only")
    parser.add_argument("--sleep", type=float, default=1.0, help="seconds to wait between register and query")
    args = parser.parse_args()

    token = os.environ.get("API_TOKEN_17TRACK")
    if not token:
        print("API_TOKEN_17TRACK is not set", file=sys.stderr)
        return 2

    number = args.number.strip()
    payload_item = carrier_payload(number, args.carrier)
    carrier_value = payload_item.get("carrier")

    register_response: dict[str, Any] = {"skipped": True}
    if not args.no_register:
        register_response = post("register", [payload_item], token)
        # Duplicate registration is normal and not fatal.
        time.sleep(max(0.0, args.sleep))

    query_response = post("gettrackinfo", [payload_item], token)

    if args.raw:
        print(json.dumps({"register": register_response, "query": query_response}, indent=2, ensure_ascii=False))
    else:
        print(
            json.dumps(
                extract_summary(number, carrier_value if isinstance(carrier_value, int) else None, query_response, register_response),
                indent=2,
                ensure_ascii=False,
            )
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
