---
name: firecrawl-carrier-tracking
description: "Uses Firecrawl MCP for rendered scraping and extraction from carrier tracking pages. Use when carrier pages need JavaScript rendering, when extracting ETA/status/current location from FedEx, UPS, DHL, freight, courier, or tracking URLs, or when enriching shipment-tracker records with carrier ETA."
---

# Firecrawl Carrier Tracking

Use this skill to extract rendered carrier tracking information through Firecrawl MCP.

## Requirements

- Firecrawl API key must be available as `FIRECRAWL_API_KEY`.
- Never print the API key.
- Remote MCP endpoint pattern: `https://mcp.firecrawl.dev/{FIRECRAWL_API_KEY}/v2/mcp`.
- The endpoint `https://mcp.firecrawl.dev` is documentation only, not the MCP endpoint.

## Critical rules

- Use Firecrawl for JavaScript-rendered carrier pages before declaring ETA unavailable.
- Extract at least: carrier, tracking number, status, ETA or estimated arrival, current location, last event, delivered date/proof if visible, source URL, and confidence.
- If ETA is visible, pass it to the shipment tracker as `records.expected_date` or tracking `eta`.
- If ETA is not found, report which Firecrawl method was tried and why ETA is missing.
- Do not confuse Odoo picking `done` with carrier delivery. Carrier page status wins.

## Quick usage

Use the wrapper script from this skill directory:

```bash
python scripts/firecrawl_tracking.py scrape "https://www.fedex.com/wtrk/track/?trknbr=872922612240"
python scripts/firecrawl_tracking.py extract "https://www.fedex.com/wtrk/track/?trknbr=872922612240"
python scripts/firecrawl_tracking.py agent "https://www.fedex.com/wtrk/track/?trknbr=872922612240"
```

Methods:

- `scrape`: calls `firecrawl_scrape` with rendered markdown and structured JSON extraction options. This is the preferred method for JavaScript-heavy carrier pages.
- `extract`: calls `firecrawl_extract` with a carrier tracking schema as a legacy fallback if `scrape` does not return structured data.
- `agent`: calls `firecrawl_agent`, then polls `firecrawl_agent_status`; best for JavaScript-heavy tracking pages that normal scrape cannot read.

## Recommended workflow for shipment ETA

1. Use `scrape` first with a wait time long enough for JavaScript-rendered carrier tracking details, typically 5000 to 10000 ms.
2. If `scrape` returns rendered content but lacks structured ETA/status fields, inspect the markdown and update from visible evidence.
3. If `scrape` fails or the content is not enough, use `agent`.
4. Use `extract` only as a legacy fallback when the current Firecrawl toolset supports it and `scrape`/`agent` are insufficient.
5. Update the shipment tracker with ETA/status if found.
6. If ETA is unavailable, add a shipment note documenting Firecrawl attempts.

Read `references/carrier-eta-workflow.md` for the complete enrichment pattern.
