---
name: 17track-package-tracking
description: "Use the 17TRACK v2.4 API for package tracking before scraping carrier pages. Uses the working register + gettrackinfo workflow and supports FedEx, UPS, and other carrier codes."
---

# 17TRACK Package Tracking

Use this skill to query package tracking through the 17TRACK v2.4 API before scraping carrier pages.

## Purpose

This is the preferred tracking approach when Odoo does not contain delivery confirmation. 17TRACK is a structured tracking API aggregator and is less fragile than FedEx/DHL/UPS public page scraping.

## Required secret

```text
API_TOKEN_17TRACK
```

Never print the token.

## Current implementation

The installed npm MCP package `mcp-server-17track@1.1.3` calls:

```text
POST https://api.17track.net/track/v2.4/getRealTimeTrackInfo
```

Verivolt's current token is not authorized for that separately gated endpoint and returns:

```json
{
  "code": -18019912,
  "message": "The real-time query interface is not authorized."
}
```

Therefore the operational wrapper uses the standard working workflow instead:

1. `POST /track/v2.4/register`
2. `POST /track/v2.4/gettrackinfo`

This workflow has been tested successfully for FedEx tracking `872922612240` with carrier code `100003`.

## Quick usage

From the shared workspace repository root:

```powershell
python skills/17track-package-tracking/scripts/track17.py 872922612240 --carrier fedex
```

Raw API responses:

```powershell
python skills/17track-package-tracking/scripts/track17.py 872922612240 --carrier fedex --raw
```

Skip registration if the tracking number was already registered:

```powershell
python skills/17track-package-tracking/scripts/track17.py 872922612240 --carrier fedex --no-register
```

## Carrier codes

Known useful aliases in the wrapper:

| Alias | 17TRACK carrier code | Notes |
|---|---:|---|
| `fedex`, `fedex-fdx`, `fdx` | `100003` | Worked for FedEx `872922612240` |
| `ups` | `100002` | 17TRACK identifies this as UPS |

If auto-detection fails with `Carrier cannot be detected`, provide the carrier code explicitly.

## Output fields

The wrapper returns normalized JSON including:

- `status`: `delivered`, `in_transit`, `exception`, `not_found`, or `unknown`
- `status_raw` and `sub_status`
- `latest_event.time_utc`
- `latest_event.description`
- `latest_event.location`
- `eta`, `eta_to`, and `eta_source`
- `delivered_at` when delivered
- origin and destination address fragments
- raw register/query responses for auditability

## Tested result

FedEx tracking `872922612240` with `--carrier fedex --no-register` returned:

- Status: `InTransit`
- Normalized status: `in_transit`
- Latest event: `On the way`
- Latest event location: `ROISSY CHARLES DE GAULLE CEDEX, 95, FR`
- Latest event UTC: `2026-06-12T20:46:00Z`
- Origin: San Francisco, CA, US
- Destination: Noventa Padovana, PD, Italy
- ETA: `2026-06-16T20:00:00-04:00`
- ETA source: `Official`

## Workflow

1. Ask Oddete/Odoo for SO, picking, carrier, tracking number, customer, and Odoo delivery fields.
2. Query 17TRACK using this skill.
3. Normalize to shipment tracker fields:
   - `delivered` -> `movement_status=delivered`
   - `in_transit` -> `movement_status=in_transit`
   - `exception` -> `movement_status=exception`
   - ETA -> tracker expected date
   - latest event/location -> tracking event or shipment note
4. Use Firecrawl/carrier-page scraping only as fallback after Odoo and 17TRACK are unavailable or insufficient.

## Limits and cautions

- 17TRACK documents a rate limit of 3 requests/second. Throttle bulk checks.
- The free plan may limit tracking numbers per month.
- `mcp-server-17track@1.1.3` still exists locally, but the operational wrapper bypasses it until real-time API permission is enabled or the MCP package is patched upstream.
