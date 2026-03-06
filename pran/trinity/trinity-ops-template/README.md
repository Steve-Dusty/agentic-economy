# Trinity Operations Template

A template for creating an operations agent that manages Trinity Deep Agent Platform instances.

## Quick Start

1. **Copy this template** to your own `trinity-ops` directory
2. **Create an instance** by copying `instances/example/` to `instances/your-instance-name/`
3. **Configure credentials** in `.env` (copy from `.env.example`)
4. **Test connection** with `./scripts/status.sh`

## Structure

```
trinity-ops/
├── CLAUDE.md              # Master operations guide (read by Claude)
├── .gitignore             # Protects credentials from commits
├── .mcp.json.template     # Template for MCP access
├── .env.example           # Example environment variables
├── playbooks/             # Standard operating procedures
│   ├── monitoring-instance.md
│   └── upgrade-instance.md
└── instances/
    └── example/           # Template instance (copy and customize)
        ├── CLAUDE.md      # Instance-specific guide
        ├── .env.example   # Instance credentials template
        ├── scripts/       # Helper scripts
        │   ├── status.sh
        │   ├── health-check.sh
        │   ├── update.sh
        │   ├── rollback.sh
        │   ├── tunnel.sh
        │   ├── restart.sh
        │   └── analyze-logs.sh
        └── .claude/
            └── commands/  # Slash commands for this instance
```

## Adding a New Instance

```bash
# 1. Copy template
cp -r instances/example instances/my-server

# 2. Edit instance CLAUDE.md with server details
# 3. Copy .env.example to .env and fill in credentials
cd instances/my-server
cp .env.example .env
nano .env

# 4. Update script paths in .claude/commands/*.md
# 5. Test connection
./scripts/status.sh
```

## Security

- **NEVER commit `.env` files** - They contain credentials
- **NEVER commit `.mcp.json`** - It contains API keys
- All sensitive files are in `.gitignore`

## Requirements

- `sshpass` - For non-interactive SSH (`brew install sshpass` or `apt install sshpass`)
- `jq` - For JSON parsing (`brew install jq` or `apt install jq`)
- SSH access to your Trinity instances

## Using with Claude Code

This template is designed to work with Claude Code. When using Claude:

1. Navigate to your `trinity-ops` directory
2. Claude will read `CLAUDE.md` for context
3. Use slash commands like `/status`, `/health`, `/update`
4. Or ask Claude to perform operations directly

## Playbooks

- **monitoring-instance.md** - How to monitor instance health
- **upgrade-instance.md** - How to safely upgrade an instance

---

*Part of the Trinity Deep Agent Orchestration Platform*
