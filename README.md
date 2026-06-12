# agent-workspace

Shared workspace for reusable agent capabilities.

This repository is intended for storing and sharing reusable resources that can be accessed, reused, and improved by team members and external contributors.

## Repository structure

```text
agent-workspace/
├── skills/
└── extensions/
```

## `skills/`

Store reusable skills, prompts, workflows, and agent capabilities in this directory.

Examples:

- Letta Code skills
- Prompt templates
- Agent workflows
- Reusable operating procedures
- Domain-specific capability packages

## `extensions/`

Store extensions, integrations, plugins, MCP servers, and related resources in this directory.

Examples:

- Letta Code extensions
- API integrations
- MCP servers
- Local plugins
- Extension documentation and examples

## Current skills

- [`skills/17track-package-tracking/`](skills/17track-package-tracking/) - Experimental 17TRACK package tracking skill using the working v2.4 register + gettrackinfo API flow before carrier-page scraping.

## Current extensions

- [`extensions/apollo-api/`](extensions/apollo-api/) - Apollo.io API extension for Letta Code tools and people/user enrichment workflows.
- [`extensions/17track-mcp/`](extensions/17track-mcp/) - Experimental local MCP package record for `mcp-server-17track@1.1.3`; retained for reference, but not operationally used until 17TRACK real-time API permission is enabled or the package is patched and dependency risk is reviewed.

## Security notes

Do not commit secrets, tokens, API keys, local config files, or generated caches.

Use environment variables, secret managers, or local ignored config files for credentials.
