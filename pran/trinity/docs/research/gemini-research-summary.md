# Gemini CLI Research - Trinity Universal Runtime Support

## Key Findings

### ✅ Gemini CLI IS MCP-Compatible!

**Package:** `@google/gemini-cli` (npm)
**Version:** 0.22.4 (as of Dec 2025)

### MCP Support
```bash
gemini mcp add <name> <commandOrUrl> [args...]  # Add MCP server
gemini mcp remove <name>                        # Remove server
gemini mcp list                                 # List configured servers
```

**Important:** Gemini CLI uses its OWN MCP configuration format (not `.mcp.json`).
It stores MCP servers via CLI commands, similar to how npm manages global packages.

### CLI Feature Parity with Claude Code

| Feature | Claude Code | Gemini CLI | Compatible? |
|---------|-------------|------------|-------------|
| **Output Format** | `--output-format stream-json` | `--output-format stream-json` | ✅ YES |
| **Tool Restrictions** | `--allowedTools` | `--allowed-tools` | ✅ YES |
| **Session Continuity** | `--continue` | `--resume` | ✅ YES |
| **MCP Support** | `.mcp.json` file | `gemini mcp add` command | ⚠️ DIFFERENT |
| **Non-interactive** | `--print` | `-p/--prompt` | ✅ YES |
| **YOLO Mode** | `--dangerously-skip-permissions` | `--yolo` or `--approval-mode yolo` | ✅ YES |

### Context Window
- **Gemini:** 1 million tokens (5x larger than Claude Code!)
- **Claude Code:** 200K tokens

### Pricing
- **Gemini:** FREE tier (60 req/min, 1K/day)
- **Claude Code:** Pay-per-use (API costs)

## Trinity Integration Path

### Option 1: Adapter Layer (Recommended)
Create a `GeminiAdapter` that translates Trinity's interface:

```python
# agent_server/services/gemini_adapter.py
class GeminiRuntime:
    def execute(prompt, mcp_servers):
        # 1. Configure MCP servers via "gemini mcp add"
        for server_name, server_config in mcp_servers.items():
            subprocess.run(["gemini", "mcp", "add", server_name, ...])

        # 2. Execute with same flags as Claude Code
        result = subprocess.run([
            "gemini",
            "--output-format", "stream-json",
            "--prompt", prompt,
            "--resume"  # for session continuity
        ])

        return parse_stream_json_output(result.stdout)
```

### Option 2: Runtime Selector in Templates
```yaml
# template.yaml
runtime:
  type: gemini-cli  # or "claude-code"
  model: gemini-2.5-pro
  max_context: 1000000
```

### Key Differences to Handle
1. **MCP Config:** Gemini uses `gemini mcp add` instead of `.mcp.json`
2. **Authentication:** Needs `GOOGLE_API_KEY` instead of `ANTHROPIC_API_KEY`
3. **Session Format:** `--resume` works differently than `--continue`

## Next Steps

1. **Prototype:** Create `gemini_adapter.py` that mirrors `claude_code.py`
2. **Test:** Run side-by-side comparison of same task
3. **Bridge:** Build MCP config translator (`.mcp.json` → `gemini mcp add` commands)
4. **Extend:** Add runtime selector to `AgentConfig` model

## Business Value

**Cost Savings:**
- Run 10 Gemini agents free vs $5-10/day for Claude
- Use Gemini for simple tasks, Claude for complex reasoning

**Redundancy:**
- If Anthropic API is down, Gemini keeps working
- Multi-cloud strategy

**Feature Access:**
- 1M context window for huge codebases
- Google Search integration built-in

