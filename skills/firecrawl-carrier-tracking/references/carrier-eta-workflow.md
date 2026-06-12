# Carrier ETA Workflow

Use this workflow to enrich any ongoing or upcoming shipment with carrier ETA.

## Source priority

1. Carrier API or official carrier integration, if available.
2. Odoo carrier fields, without treating picking `done` as carrier delivery.
3. 17TRACK structured tracking, when authorized and available.
4. Firecrawl rendered extraction from the carrier tracking page.
5. Shipment documents or labels.
6. User-provided ETA with source note.

## Preferred Firecrawl method

For JavaScript-heavy carrier pages, use `firecrawl_scrape` with:

- `formats`: `["json", "markdown"]`
- `jsonOptions.prompt`: a structured carrier-tracking extraction prompt
- `jsonOptions.schema`: the structured output target below
- `waitFor`: 5000 to 10000 ms when the page needs time to render

Use `firecrawl_extract` only as a fallback where available. It is not the preferred path for the FedEx-style JavaScript tracking case Diana validated on 2026-06-12.

## Firecrawl MCP tools

Relevant tools:

- `firecrawl_scrape`: scrape one URL with rendered content options.
- `firecrawl_extract`: extract structured data from URLs using a schema.
- `firecrawl_agent`: autonomous browser/research job for difficult JavaScript-heavy pages.
- `firecrawl_agent_status`: poll agent jobs until complete.
- `firecrawl_browser_create`, `firecrawl_browser_execute`, `firecrawl_browser_delete`: advanced browser sessions.

## Structured output target

```json
{
  "carrier": "fedex",
  "tracking_number": "872922612240",
  "status": "in_transit",
  "eta": "YYYY-MM-DD",
  "eta_text": "estimated delivery Friday ...",
  "current_location": "...",
  "last_event": "...",
  "delivered_at": null,
  "signed_by": null,
  "source_url": "https://...",
  "confidence": "high",
  "notes": "..."
}
```

## Shipment tracker update rule

When ETA is found:

- Set `records.expected_date` if there is a single shipment-level ETA.
- Set tracking `eta` if the ETA is tied to a specific tracking entry.
- Add an activity note: `ETA set from <carrier/source>: <date/text>`.

When ETA is not found:

- Leave date blank.
- Add an activity note: `ETA missing: checked Firecrawl <method(s)> for <URL>; ETA not visible/extractable.`
- Tell the user that ETA is still missing.

## Carrier status mapping

- `Delivered` / proof of delivery visible -> `movement_status=delivered`.
- `In transit`, `On the way`, `Departed`, `Arrived at facility` -> `movement_status=in_transit`.
- `Clearance delay`, customs hold/review -> `movement_status=at_customs` or `exception` depending on severity.
- `Label created`, `Shipment information sent`, pickup not confirmed -> `movement_status=awaiting`.
- `Exception`, delayed, damaged, refused, returned, address problem -> `movement_status=exception`.
