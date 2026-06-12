# 17TRACK MCP Extension

This directory records the local MCP dependency originally evaluated for the `17track-package-tracking` skill.

## Status

Experimental candidate as of 2026-06-12. The npm MCP package is retained for reference, but it is not the operational tracking path.

The operational wrapper now bypasses the MCP package and calls the working 17TRACK v2.4 standard flow directly:

1. `POST /track/v2.4/register`
2. `POST /track/v2.4/gettrackinfo`

Use the wrapper in `skills/17track-package-tracking/scripts/track17.py` for tracking lookups.

## Install

From the shared workspace repository root:

```powershell
npm install --prefix extensions/17track-mcp
```

Set the API token in the local environment or secret manager:

```text
API_TOKEN_17TRACK
```

Never commit the token or print it in logs.

## MCP server

Package:

```text
mcp-server-17track@1.1.3
```

Server entrypoint after install:

```text
extensions/17track-mcp/node_modules/mcp-server-17track/index.js
```

Tool exposed:

```text
track_package
```

Input:

```json
{
  "number": "tracking_number"
}
```

The package calls:

```text
https://api.17track.net/track/v2.4/getRealTimeTrackInfo
```

## Known blocker

Diana tested this integration on 2026-06-12. The server listed tools successfully and the wrapper ran, but a FedEx test for `872922612240` returned 17TRACK code `-18019912` with message `The real-time query interface is not authorized`.

This means the current account/token reached 17TRACK but is not authorized for the package's separately gated real-time query endpoint. Do not use the MCP package for operational tracking unless real-time endpoint permission is enabled or the package is patched upstream to use the standard register + gettrackinfo workflow.

## Working direct API path

The skill wrapper uses the working v2.4 standard API flow directly and does not require this MCP package for normal operation:

```powershell
python skills/17track-package-tracking/scripts/track17.py 872922612240 --carrier fedex --no-register
```

FedEx tracking `872922612240` with carrier code `100003` returned a normalized `in_transit` status, latest event `On the way` at `ROISSY CHARLES DE GAULLE CEDEX, 95, FR`, latest event UTC `2026-06-12T20:46:00Z`, ETA `2026-06-16T20:00:00-04:00`, ETA source `Official`.

## Security review note

`npm audit --omit=dev` on 2026-06-12 reported two high vulnerabilities via `@modelcontextprotocol/sdk <=1.25.1`, pulled by `mcp-server-17track@1.1.3`:

- GHSA-8r9q-7v3j-jr4g - ReDoS vulnerability
- GHSA-w48q-cv73-mx4w - DNS rebinding protection not enabled by default

NPM reported no fix available through this package version on 2026-06-12.

Risk context: this package is intended for stdio use by local trusted agents, not as a public HTTP service. That reduces direct DNS rebinding exposure, but it does not remove dependency risk. Broad deployment should wait for owner/security acceptance or a package update that moves to a fixed MCP SDK.

## Operational rule

If the MCP package returns an authorization error, do not infer shipment state from the error. Use the direct API wrapper, then use Odoo and carrier-source fallback methods if 17TRACK is unavailable or insufficient.
