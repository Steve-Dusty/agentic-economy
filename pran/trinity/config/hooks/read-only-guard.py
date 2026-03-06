#!/usr/bin/env python3
"""
Read-Only Mode Guard - PreToolUse hook for Trinity agents.
Blocks Write/Edit/NotebookEdit operations to protected paths.

Input: JSON via stdin with tool_input.file_path
Output: Exit 0 to allow, Exit 2 with stderr message to block

Reference: https://docs.anthropic.com/en/docs/claude-code/hooks
"""
import os
import sys
import json
import fnmatch

# Load config from file (written by platform on agent start)
CONFIG_PATH = os.path.expanduser("~/.trinity/read-only-config.json")

# Default patterns if no config file exists
DEFAULT_BLOCKED = [
    "*.py", "*.js", "*.ts", "*.jsx", "*.tsx", "*.vue", "*.svelte",
    "*.go", "*.rs", "*.rb", "*.java", "*.c", "*.cpp", "*.h",
    "*.sh", "*.bash", "Makefile", "Dockerfile",
    "CLAUDE.md", "README.md", ".claude/*", ".env", ".env.*",
    "template.yaml", "*.yaml", "*.yml", "*.json", "*.toml"
]

DEFAULT_ALLOWED = [
    "content/*", "output/*", "reports/*", "exports/*",
    "*.log", "*.txt"
]


def load_config():
    """Load configuration from file or use defaults."""
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH) as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            pass
    return {
        "blocked_patterns": DEFAULT_BLOCKED,
        "allowed_patterns": DEFAULT_ALLOWED
    }


def matches_any(path: str, patterns: list) -> bool:
    """Check if path matches any of the glob patterns."""
    # Normalize path - remove leading /home/developer/ or ./
    if path.startswith("/home/developer/"):
        path = path[len("/home/developer/"):]
    elif path.startswith("./"):
        path = path[2:]

    # Resolve to absolute and back to relative to handle ../ etc
    # This is a simple normalization, not full symlink resolution
    parts = []
    for part in path.split("/"):
        if part == "..":
            if parts:
                parts.pop()
        elif part and part != ".":
            parts.append(part)
    normalized_path = "/".join(parts)

    basename = os.path.basename(normalized_path)

    for pattern in patterns:
        # Match against full path
        if fnmatch.fnmatch(normalized_path, pattern):
            return True
        # Match against basename (for patterns like "*.py")
        if fnmatch.fnmatch(basename, pattern):
            return True
        # Handle directory wildcards (e.g., ".claude/*")
        if pattern.endswith("/*"):
            dir_pattern = pattern[:-2]
            if normalized_path.startswith(dir_pattern + "/") or normalized_path == dir_pattern:
                return True
    return False


def main():
    # Read JSON input from stdin (Claude Code hook protocol)
    try:
        data = json.load(sys.stdin)
    except json.JSONDecodeError:
        # Can't parse input, allow by default (fail open)
        sys.exit(0)

    # Extract file_path from tool_input
    tool_input = data.get("tool_input", {})
    file_path = tool_input.get("file_path", "")

    # Also check notebook_path for NotebookEdit
    if not file_path:
        file_path = tool_input.get("notebook_path", "")

    if not file_path:
        # No file path in input, allow
        sys.exit(0)

    config = load_config()
    blocked = config.get("blocked_patterns", DEFAULT_BLOCKED)
    allowed = config.get("allowed_patterns", DEFAULT_ALLOWED)

    # Allowed patterns take precedence
    if matches_any(file_path, allowed):
        sys.exit(0)  # Allow

    # Check blocked patterns
    if matches_any(file_path, blocked):
        # Exit 2 with stderr = block with feedback to Claude
        print(f"Read-only mode: Cannot modify '{file_path}' (protected path)", file=sys.stderr)
        sys.exit(2)

    # Default: allow (anything not explicitly blocked is permitted)
    sys.exit(0)


if __name__ == "__main__":
    main()
