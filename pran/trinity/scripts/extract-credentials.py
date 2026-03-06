#!/usr/bin/env python3
"""
Extract credential requirements from an agent repository.

Scans for:
1. ${VAR_NAME} patterns in .mcp.json or .mcp.json.template
2. Structured credentials section in template.yaml
3. Variables in .env.example (if present)

Usage:
    python extract-credentials.py /path/to/agent/repo

Output: JSON with required credentials and their sources
"""

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Optional


def extract_env_vars_from_mcp_json(file_path: Path) -> dict[str, list[str]]:
    """
    Extract ${VAR_NAME} patterns from .mcp.json or .mcp.json.template

    Returns dict mapping MCP server name to list of env vars it requires
    """
    if not file_path.exists():
        return {}

    try:
        with open(file_path) as f:
            content = f.read()
            data = json.loads(content)
    except (json.JSONDecodeError, IOError) as e:
        print(f"Warning: Could not parse {file_path}: {e}", file=sys.stderr)
        return {}

    # Pattern to match ${VAR_NAME} - captures the VAR_NAME part
    pattern = r'\$\{([A-Z][A-Z0-9_]*)\}'

    result = {}
    mcp_servers = data.get("mcpServers", {})

    for server_name, server_config in mcp_servers.items():
        vars_for_server = set()

        # Search in env section
        if "env" in server_config:
            for key, value in server_config["env"].items():
                if isinstance(value, str):
                    matches = re.findall(pattern, value)
                    vars_for_server.update(matches)

        # Search in args array (some servers like cloudinary put creds in args)
        if "args" in server_config:
            for arg in server_config["args"]:
                if isinstance(arg, str):
                    matches = re.findall(pattern, arg)
                    vars_for_server.update(matches)

        if vars_for_server:
            result[server_name] = sorted(vars_for_server)

    return result


def extract_from_template_yaml(file_path: Path) -> dict:
    """
    Extract credentials section from template.yaml

    Returns structured dict with mcp_servers, env_file, and config_files
    """
    if not file_path.exists():
        return {}

    try:
        import yaml
        with open(file_path) as f:
            data = yaml.safe_load(f)
    except Exception as e:
        print(f"Warning: Could not parse {file_path}: {e}", file=sys.stderr)
        return {}

    credentials = data.get("credentials", {})
    return credentials


def extract_from_env_example(file_path: Path) -> list[str]:
    """
    Extract variable names from .env.example

    Returns list of variable names
    """
    if not file_path.exists():
        return []

    vars = []
    try:
        with open(file_path) as f:
            for line in f:
                line = line.strip()
                # Skip comments and empty lines
                if not line or line.startswith('#'):
                    continue
                # Extract variable name (before = sign)
                if '=' in line:
                    var_name = line.split('=')[0].strip()
                    if var_name and re.match(r'^[A-Z][A-Z0-9_]*$', var_name):
                        vars.append(var_name)
    except IOError as e:
        print(f"Warning: Could not read {file_path}: {e}", file=sys.stderr)

    return vars


def extract_credentials(repo_path: Path) -> dict:
    """
    Extract all credential requirements from an agent repository.

    Returns:
        {
            "required_credentials": [
                {
                    "name": "HEYGEN_API_KEY",
                    "source": "mcp:heygen",
                    "description": "API key for HeyGen video generation"
                },
                ...
            ],
            "mcp_servers": {
                "heygen": ["HEYGEN_API_KEY"],
                "twitter-mcp": ["TWITTER_API_KEY", "TWITTER_API_SECRET_KEY", ...]
            },
            "env_file_vars": ["BLOTATO_API_KEY", ...],
            "sources": {
                ".mcp.json": true,
                "template.yaml": true,
                ".env.example": false
            }
        }
    """
    result = {
        "required_credentials": [],
        "mcp_servers": {},
        "env_file_vars": [],
        "sources": {
            ".mcp.json": False,
            ".mcp.json.template": False,
            "template.yaml": False,
            ".env.example": False
        }
    }

    # Track all unique vars and their sources
    all_vars = {}  # var_name -> list of sources

    # 1. Check .mcp.json or .mcp.json.template
    mcp_json = repo_path / ".mcp.json"
    mcp_template = repo_path / ".mcp.json.template"

    if mcp_json.exists():
        mcp_servers = extract_env_vars_from_mcp_json(mcp_json)
        result["sources"][".mcp.json"] = True
    elif mcp_template.exists():
        mcp_servers = extract_env_vars_from_mcp_json(mcp_template)
        result["sources"][".mcp.json.template"] = True
    else:
        mcp_servers = {}

    result["mcp_servers"] = mcp_servers

    for server_name, vars in mcp_servers.items():
        for var in vars:
            if var not in all_vars:
                all_vars[var] = []
            all_vars[var].append(f"mcp:{server_name}")

    # 2. Check template.yaml
    template_yaml = repo_path / "template.yaml"
    if template_yaml.exists():
        result["sources"]["template.yaml"] = True
        template_creds = extract_from_template_yaml(template_yaml)

        # Extract from mcp_servers section
        for server_name, server_config in template_creds.get("mcp_servers", {}).items():
            env_vars = server_config.get("env_vars", [])
            for var in env_vars:
                if var not in all_vars:
                    all_vars[var] = []
                if f"mcp:{server_name}" not in all_vars[var]:
                    all_vars[var].append(f"template:mcp:{server_name}")

        # Extract from env_file section
        env_file_vars = template_creds.get("env_file", [])
        result["env_file_vars"] = env_file_vars
        for var in env_file_vars:
            if var not in all_vars:
                all_vars[var] = []
            all_vars[var].append("template:env_file")

    # 3. Check .env.example
    env_example = repo_path / ".env.example"
    if env_example.exists():
        result["sources"][".env.example"] = True
        env_vars = extract_from_env_example(env_example)
        for var in env_vars:
            if var not in all_vars:
                all_vars[var] = []
            all_vars[var].append(".env.example")

    # Build the consolidated list
    for var_name in sorted(all_vars.keys()):
        sources = all_vars[var_name]
        # Determine the primary source for display
        primary_source = sources[0] if sources else "unknown"

        result["required_credentials"].append({
            "name": var_name,
            "source": primary_source,
            "all_sources": sources
        })

    return result


def main():
    parser = argparse.ArgumentParser(
        description="Extract credential requirements from an agent repository"
    )
    parser.add_argument(
        "repo_path",
        type=Path,
        help="Path to the agent repository"
    )
    parser.add_argument(
        "--format",
        choices=["json", "table"],
        default="json",
        help="Output format (default: json)"
    )

    args = parser.parse_args()

    if not args.repo_path.exists():
        print(f"Error: Path does not exist: {args.repo_path}", file=sys.stderr)
        sys.exit(1)

    result = extract_credentials(args.repo_path)

    if args.format == "json":
        print(json.dumps(result, indent=2))
    else:
        # Table format
        print(f"\nCredential Requirements for: {args.repo_path.name}")
        print("=" * 60)

        if not result["required_credentials"]:
            print("No credentials required.")
        else:
            print(f"\n{'Variable Name':<40} {'Source':<20}")
            print("-" * 60)
            for cred in result["required_credentials"]:
                print(f"{cred['name']:<40} {cred['source']:<20}")

        print(f"\n\nSources checked:")
        for source, found in result["sources"].items():
            status = "✓" if found else "✗"
            print(f"  {status} {source}")

        print(f"\nTotal: {len(result['required_credentials'])} unique credentials required")


if __name__ == "__main__":
    main()
