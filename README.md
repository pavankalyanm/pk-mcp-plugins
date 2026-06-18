# Claude Plugins

A marketplace of MCP plugins for **Claude Code** and **Claude Desktop**.

## Install

In Claude Code → Add marketplace → paste:

```
https://github.com/pavankalyanm/claude-plugins.git
```

## Plugins

| Plugin | Description |
|--------|-------------|
| [mails-bridge](mails-bridge/) | Multi-account email via IMAP/SMTP — Gmail, Outlook, Yahoo, iCloud, and more |

## Adding a new plugin

1. Create `<plugin-name>/` with `.claude-plugin/plugin.json`, `.mcp.json`, `server/`, and `skills/`
2. Add an entry to `.claude-plugin/marketplace.json`

## Requirements

- Python 3.11+
- [uv](https://docs.astral.sh/uv/) package manager
