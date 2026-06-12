---
name: 17track-package-tracking
description: "Use the 17TRACK MCP server/API for package tracking before scraping carrier pages. Supports FedEx, DHL, UPS, USPS, and other carriers when API_TOKEN_17TRACK is authorized."
---

# 17TRACK Package Tracking

Use this skill to query package tracking through the `mcp-server-17track` MCP server.

## Status

Experimental candidate as of 2026-06-12. Do not treat this as production-approved until both gates are cleared:

1. 17TRACK account/API permission is enabled for the endpoint used by the package, or an alternate 17TRACK register/query workflow is implemented.
2. The dependency risk from `@modelcontextprotocol/sdk <=1.25.1` is accepted by security/owner review or resolved by an upstream package update.

## Purpose

This is the preferred structured tracking approach before carrier-page scraping when Odoo does not contain delivery confirmation. 17TRACK is an API aggregator and is less fragile than scraping FedEx, DHL, UPS, or USPS public tracking pages.

## Required extension

This skill expects the companion extension at:

```text
extensions/17track-mcp/
```

Install from the shared workspace repository root:

```powershell
npm install --prefix extensions/17track-mcp
```

Required secret/env var:

```text
API_TOKEN_17TRACK
```

Never print the token, commit it, or place it in skill files.

## Current authorization status

Diana tested `mcp-server-17track@1.1.3` on 2026-06-12. The MCP server starts and lists tools successfully. A test call for FedEx tracking number `872922612240` returned:

```json
{
  "code": -18019912,
  "message": "The real-time query interface is not authorized."
}
```

This means the token reached 17TRACK, but the account was not authorized for the package's `getRealTimeTrackInfo` real-time endpoint. The account likely needs real-time query API permission enabled, or the workflow needs to use another supported 17TRACK endpoint pattern such as register plus query/webhook.

## Tools exposed

The MCP exposes one tool:

```text
track_package
```

Input schema:

```json
{
  "number": "tracking_number"
}
```

## Quick usage

Use the Windows-safe wrapper from the shared workspace repository root:

```powershell
python skills/17track-package-tracking/scripts/track17.py 872922612240
```

The wrapper reads `API_TOKEN_17TRACK` from the environment and calls the MCP server over stdio. It does not print the token.

## Workflow

1. Ask Oddete/Odoo for the sales order, picking, carrier, tracking number, customer, and Odoo delivery fields.
2. Query 17TRACK using this skill.
3. If 17TRACK returns authorized structured tracking, normalize to shipment tracker fields:
   - Delivered -> `movement_status=delivered`
   - In transit or out for delivery -> `movement_status=in_transit`
   - Exception -> `movement_status=exception`
   - ETA -> tracker expected date
   - Latest event/location -> tracking event or note
4. If 17TRACK returns an authorization error, do not infer status. Report that 17TRACK needs API permission enabled or an alternate endpoint workflow.
5. Use [`firecrawl-carrier-tracking`](../firecrawl-carrier-tracking/) or another carrier-page scraping method only as a fallback after Odoo and 17TRACK are unavailable or insufficient.

## Rate limits and duplicate avoidance

17TRACK public documentation has referenced a 3 requests/second API limit and a 100 free tracking numbers/month free tier. Bulk checks should throttle and avoid duplicate queries.

## Security notes

`npm audit --omit=dev` on 2026-06-12 reported two high vulnerabilities through `@modelcontextprotocol/sdk <=1.25.1`, pulled by `mcp-server-17track@1.1.3`:

- ReDoS vulnerability
- DNS rebinding protection not enabled by default

No fixed dependency path was available through this package version on 2026-06-12. Because this server is used over stdio by local trusted callers, the DNS rebinding issue is less directly exposed than it would be for an HTTP server, but the dependency risk still needs explicit owner/security acceptance before broad deployment.
