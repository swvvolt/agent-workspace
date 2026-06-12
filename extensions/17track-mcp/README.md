# 17TRACK MCP Extension

This directory records the local MCP dependency used by the `17track-package-tracking` skill.

## Status

Experimental candidate as of 2026-06-12. Not approved for broad production deployment until the authorization and dependency-risk gates below are resolved.

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

This means the current account/token needs real-time query permission, or the workflow should be changed to a different 17TRACK endpoint pattern such as registering tracking numbers and querying/webhooking status later.

## Security review note

`npm audit --omit=dev` on 2026-06-12 reported two high vulnerabilities via `@modelcontextprotocol/sdk <=1.25.1`, pulled by `mcp-server-17track@1.1.3`:

- GHSA-8r9q-7v3j-jr4g - ReDoS vulnerability
- GHSA-w48q-cv73-mx4w - DNS rebinding protection not enabled by default

NPM reported no fix available through this package version on 2026-06-12.

Risk context: this package is intended for stdio use by local trusted agents, not as a public HTTP service. That reduces direct DNS rebinding exposure, but it does not remove dependency risk. Broad deployment should wait for owner/security acceptance or a package update that moves to a fixed MCP SDK.

## Operational rule

If the API returns an authorization error, do not infer shipment state from the error. Report that 17TRACK permission or endpoint workflow is missing, then use Odoo and carrier-source fallback methods.
