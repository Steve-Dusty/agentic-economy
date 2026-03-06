"""
Agent Service Read-Only Mode - Code protection for deployed agents.

Handles read-only mode toggle which prevents agents from modifying
source code, instructions, or configuration files while allowing
output to designated directories.

Uses Claude Code's PreToolUse hooks to intercept Write/Edit operations.
"""
import json
import logging
import os
from typing import Dict, Optional

from fastapi import HTTPException

from models import User
from database import db
from services.docker_service import get_agent_container
from services.agent_client import get_agent_client

logger = logging.getLogger(__name__)

# Default patterns for read-only mode
DEFAULT_BLOCKED_PATTERNS = [
    "*.py", "*.js", "*.ts", "*.jsx", "*.tsx", "*.vue", "*.svelte",
    "*.go", "*.rs", "*.rb", "*.java", "*.c", "*.cpp", "*.h",
    "*.sh", "*.bash", "Makefile", "Dockerfile",
    "CLAUDE.md", "README.md", ".claude/*", ".env", ".env.*",
    "template.yaml", "*.yaml", "*.yml", "*.json", "*.toml"
]

DEFAULT_ALLOWED_PATTERNS = [
    "content/*", "output/*", "reports/*", "exports/*",
    "*.log", "*.txt"
]


def get_default_config() -> dict:
    """Get default read-only configuration."""
    return {
        "blocked_patterns": DEFAULT_BLOCKED_PATTERNS.copy(),
        "allowed_patterns": DEFAULT_ALLOWED_PATTERNS.copy()
    }


async def get_read_only_status_logic(
    agent_name: str,
    current_user: User
) -> dict:
    """
    Get the read-only mode status for an agent.

    Returns whether read-only mode is enabled and the current configuration.
    """
    if not db.can_user_access_agent(current_user.username, agent_name):
        raise HTTPException(status_code=403, detail="You don't have permission to access this agent")

    container = get_agent_container(agent_name)
    if not container:
        raise HTTPException(status_code=404, detail="Agent not found")

    read_only_data = db.get_read_only_mode(agent_name)

    return {
        "agent_name": agent_name,
        "enabled": read_only_data["enabled"],
        "config": read_only_data["config"] or get_default_config()
    }


async def set_read_only_status_logic(
    agent_name: str,
    body: dict,
    current_user: User
) -> dict:
    """
    Set the read-only mode status for an agent.

    When enabling:
    - Configuration is saved to database
    - If agent is running, hooks are injected immediately

    When disabling:
    - Setting is saved to database
    - Hooks are removed on next agent restart

    Body:
    - enabled: True to enable read-only mode, False to disable
    - config: Optional dict with 'blocked_patterns' and 'allowed_patterns'
    """
    # Only owner can modify read-only mode
    if not db.can_user_share_agent(current_user.username, agent_name):
        raise HTTPException(status_code=403, detail="Only the owner can modify read-only settings")

    container = get_agent_container(agent_name)
    if not container:
        raise HTTPException(status_code=404, detail="Agent not found")

    # Don't allow read-only for system agent
    if db.is_system_agent(agent_name):
        raise HTTPException(status_code=403, detail="Cannot modify read-only mode for system agent")

    enabled = body.get("enabled")
    if enabled is None:
        raise HTTPException(status_code=400, detail="enabled is required")

    enabled = bool(enabled)
    config = body.get("config")

    # Validate config if provided
    if config is not None:
        if not isinstance(config, dict):
            raise HTTPException(status_code=400, detail="config must be an object")
        if "blocked_patterns" in config and not isinstance(config["blocked_patterns"], list):
            raise HTTPException(status_code=400, detail="blocked_patterns must be a list")
        if "allowed_patterns" in config and not isinstance(config["allowed_patterns"], list):
            raise HTTPException(status_code=400, detail="allowed_patterns must be a list")

    # Use default config if enabling without custom config
    if enabled and config is None:
        config = get_default_config()

    # Update the database
    db.set_read_only_mode(agent_name, enabled, config)

    # If agent is running and we're enabling, inject hooks immediately
    hooks_injected = False
    if enabled and container.status == "running":
        try:
            result = await inject_read_only_hooks(agent_name, config)
            hooks_injected = result.get("success", False)
        except Exception as e:
            logger.warning(f"Failed to inject read-only hooks into running agent {agent_name}: {e}")

    logger.info(
        f"Read-only mode {'enabled' if enabled else 'disabled'} for agent {agent_name} "
        f"by {current_user.username}. Hooks injected: {hooks_injected}"
    )

    return {
        "status": "updated",
        "agent_name": agent_name,
        "enabled": enabled,
        "config": config,
        "hooks_injected": hooks_injected,
        "message": f"Read-only mode {'enabled' if enabled else 'disabled'}." + (
            " Hooks will be applied on next agent start." if enabled and not hooks_injected else ""
        )
    }


async def inject_read_only_hooks(agent_name: str, config: Optional[dict] = None) -> dict:
    """
    Inject read-only mode hooks into a running agent.

    This writes:
    1. ~/.trinity/read-only-config.json - Configuration file
    2. ~/.trinity/hooks/read-only-guard.py - Guard script
    3. Merges hook registration into ~/.claude/settings.local.json

    Args:
        agent_name: Name of the agent
        config: Read-only configuration (blocked/allowed patterns)

    Returns:
        dict with success status and details
    """
    if config is None:
        # Load from database
        read_only_data = db.get_read_only_mode(agent_name)
        if not read_only_data["enabled"]:
            return {"success": True, "skipped": True, "reason": "read_only_mode_disabled"}
        config = read_only_data["config"] or get_default_config()

    client = get_agent_client(agent_name)

    # Load the guard script from mounted config/hooks directory
    # In Docker: /config/hooks/read-only-guard.py (mounted volume)
    # In dev: relative path from backend/services/agent_service/
    guard_script_path = "/config/hooks/read-only-guard.py"
    if not os.path.exists(guard_script_path):
        # Fallback for local development
        guard_script_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))),
            "config", "hooks", "read-only-guard.py"
        )

    try:
        with open(guard_script_path, "r") as f:
            guard_script_content = f.read()
    except FileNotFoundError:
        logger.error(f"Guard script not found at {guard_script_path}")
        return {"success": False, "error": "Guard script not found"}

    # 1. Write the config file (platform=True to bypass .trinity protection)
    config_result = await client.write_file(
        ".trinity/read-only-config.json",
        json.dumps(config, indent=2),
        platform=True
    )
    if not config_result.get("success"):
        return {"success": False, "error": f"Failed to write config: {config_result.get('error')}"}

    # 2. Write the guard script (platform=True to bypass .trinity protection)
    script_result = await client.write_file(
        ".trinity/hooks/read-only-guard.py",
        guard_script_content,
        platform=True
    )
    if not script_result.get("success"):
        return {"success": False, "error": f"Failed to write guard script: {script_result.get('error')}"}

    # 3. Make the guard script executable (via a simple chmod approach)
    # The agent server handles this when writing files with .py extension

    # 4. Merge hook registration into settings.local.json
    settings_result = await _merge_hook_settings(client)
    if not settings_result.get("success"):
        return {"success": False, "error": f"Failed to merge settings: {settings_result.get('error')}"}

    logger.info(f"Read-only hooks injected into agent {agent_name}")
    return {"success": True, "files_written": 3}


async def _merge_hook_settings(client) -> dict:
    """
    Merge read-only hook registration into ~/.claude/settings.local.json.

    Preserves existing settings and hooks while adding the read-only guard.
    """
    settings_path = ".claude/settings.local.json"

    # Try to read existing settings
    existing_settings = {}
    read_result = await client.read_file(settings_path)
    if read_result.get("success") and read_result.get("content"):
        try:
            existing_settings = json.loads(read_result["content"])
        except json.JSONDecodeError:
            existing_settings = {}

    # Ensure hooks structure exists
    if "hooks" not in existing_settings:
        existing_settings["hooks"] = {}
    if "PreToolUse" not in existing_settings["hooks"]:
        existing_settings["hooks"]["PreToolUse"] = []

    # Check if our hook is already registered
    our_hook_matcher = "Write|Edit|NotebookEdit"
    our_hook_command = "python3 /home/developer/.trinity/hooks/read-only-guard.py"

    hook_exists = False
    for hook_entry in existing_settings["hooks"]["PreToolUse"]:
        if hook_entry.get("matcher") == our_hook_matcher:
            # Update existing entry
            hook_entry["hooks"] = [{"type": "command", "command": our_hook_command}]
            hook_exists = True
            break

    if not hook_exists:
        # Add new hook entry
        existing_settings["hooks"]["PreToolUse"].append({
            "matcher": our_hook_matcher,
            "hooks": [{"type": "command", "command": our_hook_command}]
        })

    # Write updated settings
    write_result = await client.write_file(
        settings_path,
        json.dumps(existing_settings, indent=2)
    )

    return write_result


async def remove_read_only_hooks(agent_name: str) -> dict:
    """
    Remove read-only mode hooks from an agent.

    This removes the hook registration from settings.local.json.
    The config and script files are left in place (harmless).

    Args:
        agent_name: Name of the agent

    Returns:
        dict with success status
    """
    client = get_agent_client(agent_name)
    settings_path = ".claude/settings.local.json"

    # Read existing settings
    read_result = await client.read_file(settings_path)
    if not read_result.get("success") or not read_result.get("content"):
        return {"success": True, "skipped": True, "reason": "no_settings_file"}

    try:
        settings = json.loads(read_result["content"])
    except json.JSONDecodeError:
        return {"success": True, "skipped": True, "reason": "invalid_settings_file"}

    # Remove our hook if present
    if "hooks" in settings and "PreToolUse" in settings["hooks"]:
        our_hook_matcher = "Write|Edit|NotebookEdit"
        settings["hooks"]["PreToolUse"] = [
            hook for hook in settings["hooks"]["PreToolUse"]
            if hook.get("matcher") != our_hook_matcher
        ]

        # Clean up empty structures
        if not settings["hooks"]["PreToolUse"]:
            del settings["hooks"]["PreToolUse"]
        if not settings["hooks"]:
            del settings["hooks"]

    # Write updated settings
    write_result = await client.write_file(
        settings_path,
        json.dumps(settings, indent=2)
    )

    return write_result
