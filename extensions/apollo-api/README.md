# Apollo API Extension

This extension provides Apollo.io API access for Letta Code workflows.

## Source

- `apollo-api.js` - local Letta Code extension source copied from the most recently created local extension at `~/.letta/extensions/apollo-api.js`.

## Capabilities

The extension exposes Apollo API workflows such as:

- people enrichment
- user search
- generic authenticated Apollo `/api/v1` requests

## Configuration

The extension expects an Apollo API key from one of these local sources:

- `APOLLO_API_KEY` environment variable
- local ignored config at `~/.letta/extensions/apollo-api.config.json`

On Windows, the local config path may store an encrypted key using Windows DPAPI.

## Security

Do **not** commit `apollo-api.config.json`, API keys, generated extension-cache files, or diagnostics containing sensitive data.

Only source code and safe documentation should be stored in this public repository.
