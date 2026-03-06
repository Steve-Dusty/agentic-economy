"""
Backend credential sanitization utility.

Defense-in-depth layer that sanitizes execution logs before database persistence.
This catches any credentials that may have bypassed agent-side sanitization.

Note: The primary sanitization should happen on the agent side. This backend
layer is a safety net for cases where the agent may not have sanitized properly.
"""

import re
import json
import logging
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)

# Secret value patterns - values that look like secrets regardless of context
SECRET_VALUE_PATTERNS = [
    r'sk-[a-zA-Z0-9]{20,}',           # OpenAI API keys
    r'sk-proj-[a-zA-Z0-9\-_]{20,}',   # OpenAI project keys
    r'sk-ant-[a-zA-Z0-9\-_]{20,}',    # Anthropic API keys
    r'ghp_[a-zA-Z0-9]{36,}',          # GitHub PAT (fine-grained)
    r'github_pat_[a-zA-Z0-9_]{22,}',  # GitHub PAT (classic)
    r'gho_[a-zA-Z0-9]{36,}',          # GitHub OAuth token
    r'ghs_[a-zA-Z0-9]{36,}',          # GitHub App token
    r'ghr_[a-zA-Z0-9]{36,}',          # GitHub refresh token
    r'xoxb-[a-zA-Z0-9\-]+',           # Slack bot token
    r'xoxp-[a-zA-Z0-9\-]+',           # Slack user token
    r'xoxa-[a-zA-Z0-9\-]+',           # Slack app token
    r'AKIA[A-Z0-9]{16}',              # AWS access key
    r'trinity_mcp_[a-zA-Z0-9]{16,}',  # Trinity MCP keys
    r'Bearer\s+[a-zA-Z0-9\-_.]+',     # Bearer tokens
    r'Basic\s+[a-zA-Z0-9+/=]+',       # Basic auth
]

# Sensitive key patterns (for key=value pairs)
SENSITIVE_KEY_PATTERNS = [
    r'.*API_KEY.*',
    r'.*API_SECRET.*',
    r'.*TOKEN.*',
    r'.*SECRET.*',
    r'.*PASSWORD.*',
    r'.*CREDENTIAL.*',
    r'.*PRIVATE_KEY.*',
    r'.*AUTH.*',
    r'ANTHROPIC_.*',
    r'OPENAI_.*',
    r'GITHUB_.*',
    r'AWS_.*',
    r'TRINITY_MCP.*',
]

# Compiled patterns
_secret_value_re = [re.compile(p) for p in SECRET_VALUE_PATTERNS]
_sensitive_key_re = [re.compile(p, re.IGNORECASE) for p in SENSITIVE_KEY_PATTERNS]

REDACTION_PLACEHOLDER = "***REDACTED***"


def sanitize_text(text: str) -> str:
    """
    Sanitize sensitive values from text.

    Args:
        text: Text that may contain sensitive values

    Returns:
        Sanitized text with credentials replaced
    """
    if not text:
        return text

    result = text

    # Replace values matching secret patterns
    for pattern in _secret_value_re:
        result = pattern.sub(REDACTION_PLACEHOLDER, result)

    # Redact key=value pairs where key is sensitive
    for key_pattern in _sensitive_key_re:
        kv_pattern = re.compile(
            r'(' + key_pattern.pattern + r')=(["\']?)([^\s"\']+)\2',
            re.IGNORECASE
        )
        result = kv_pattern.sub(r'\1=' + REDACTION_PLACEHOLDER, result)

    return result


def sanitize_dict(data: Dict[str, Any], depth: int = 0, max_depth: int = 10) -> Dict[str, Any]:
    """Recursively sanitize sensitive values in a dictionary."""
    if depth > max_depth:
        return data

    result = {}
    for key, value in data.items():
        if isinstance(value, str):
            result[key] = sanitize_text(value)
        elif isinstance(value, dict):
            result[key] = sanitize_dict(value, depth + 1, max_depth)
        elif isinstance(value, list):
            result[key] = sanitize_list(value, depth + 1, max_depth)
        else:
            result[key] = value
    return result


def sanitize_list(data: List[Any], depth: int = 0, max_depth: int = 10) -> List[Any]:
    """Recursively sanitize sensitive values in a list."""
    if depth > max_depth:
        return data

    result = []
    for item in data:
        if isinstance(item, str):
            result.append(sanitize_text(item))
        elif isinstance(item, dict):
            result.append(sanitize_dict(item, depth + 1, max_depth))
        elif isinstance(item, list):
            result.append(sanitize_list(item, depth + 1, max_depth))
        else:
            result.append(item)
    return result


def sanitize_json_string(json_str: str) -> str:
    """
    Sanitize a JSON string by parsing, sanitizing, and re-serializing.

    Args:
        json_str: JSON string that may contain sensitive values

    Returns:
        Sanitized JSON string
    """
    if not json_str:
        return json_str

    try:
        data = json.loads(json_str)
        if isinstance(data, dict):
            sanitized = sanitize_dict(data)
        elif isinstance(data, list):
            sanitized = sanitize_list(data)
        else:
            return sanitize_text(json_str)
        return json.dumps(sanitized)
    except json.JSONDecodeError:
        # If not valid JSON, sanitize as plain text
        return sanitize_text(json_str)


def sanitize_execution_log(execution_log_json: Optional[str]) -> Optional[str]:
    """
    Sanitize an execution log JSON string before database persistence.

    This is the main entry point for sanitizing execution logs in the backend.

    Args:
        execution_log_json: JSON string containing execution log

    Returns:
        Sanitized JSON string
    """
    if not execution_log_json:
        return execution_log_json

    return sanitize_json_string(execution_log_json)


def sanitize_response(response: Optional[str]) -> Optional[str]:
    """
    Sanitize an agent response before database persistence.

    Args:
        response: Agent response text

    Returns:
        Sanitized response
    """
    if not response:
        return response

    return sanitize_text(response)
