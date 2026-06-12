# Firecrawl Carrier Tracking

This shared skill provides a rendered carrier-page fallback for shipment ETA, status, current-location, and delivery-proof extraction.

Use it after structured sources such as Odoo carrier fields and authorized 17TRACK lookups are unavailable or insufficient.

Credential required at runtime:

```text
FIRECRAWL_API_KEY
```

Do not commit keys, local config, rendered carrier outputs, or generated caches.

Primary entrypoint:

```text
SKILL.md
```

Helper script:

```text
scripts/firecrawl_tracking.py
```

Workflow reference:

```text
references/carrier-eta-workflow.md
```
