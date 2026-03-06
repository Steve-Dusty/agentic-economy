"""
Template service for processing agent templates.

Metadata for GitHub templates is fetched from each repo's template.yaml
via the GitHub API and cached in memory (10-minute TTL).
"""
import base64
import json
import logging
import re
import subprocess
import shutil
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Optional
from pathlib import Path
import httpx
import yaml
from config import DEFAULT_GITHUB_TEMPLATE_REPOS, GITHUB_PAT_CREDENTIAL_ID

logger = logging.getLogger(__name__)

# ============================================================================
# GitHub Metadata Fetching & Caching
# ============================================================================

_metadata_cache: Dict[str, tuple] = {}  # repo -> (timestamp, metadata_dict)
_CACHE_TTL = 600  # 10 minutes


def _fetch_template_yaml(repo: str, pat: str) -> dict:
    """Fetch and parse template.yaml from a GitHub repo via the API.

    Returns parsed YAML dict, or empty dict if not found / error.
    """
    try:
        headers = {"Accept": "application/vnd.github+json"}
        if pat:
            headers["Authorization"] = f"Bearer {pat}"

        with httpx.Client(timeout=10.0) as client:
            resp = client.get(
                f"https://api.github.com/repos/{repo}/contents/template.yaml",
                headers=headers,
            )

        if resp.status_code != 200:
            logger.debug("template.yaml not found for %s (HTTP %s)", repo, resp.status_code)
            return {}

        data = resp.json()
        content = base64.b64decode(data["content"]).decode("utf-8")
        return yaml.safe_load(content) or {}
    except Exception as e:
        logger.warning("Failed to fetch template.yaml for %s: %s", repo, e)
        return {}


def _get_github_pat() -> str:
    """Get GitHub PAT (avoids circular import)."""
    from services.settings_service import get_github_pat
    return get_github_pat()


def _get_cached_metadata(repo: str) -> dict:
    """Return cached metadata for a repo, fetching if stale or missing."""
    cached = _metadata_cache.get(repo)
    if cached and time.time() - cached[0] < _CACHE_TTL:
        return cached[1]

    pat = _get_github_pat()
    metadata = _fetch_template_yaml(repo, pat)
    _metadata_cache[repo] = (time.time(), metadata)
    return metadata


def _fetch_all_metadata(repos: List[str]) -> Dict[str, dict]:
    """Fetch template.yaml for multiple repos, using cache and concurrency."""
    results = {}
    to_fetch = []

    for repo in repos:
        cached = _metadata_cache.get(repo)
        if cached and time.time() - cached[0] < _CACHE_TTL:
            results[repo] = cached[1]
        else:
            to_fetch.append(repo)

    if to_fetch:
        pat = _get_github_pat()
        with ThreadPoolExecutor(max_workers=5) as pool:
            futures = {
                pool.submit(_fetch_template_yaml, repo, pat): repo
                for repo in to_fetch
            }
            for future in as_completed(futures):
                repo = futures[future]
                try:
                    metadata = future.result()
                except Exception:
                    metadata = {}
                _metadata_cache[repo] = (time.time(), metadata)
                results[repo] = metadata

    return results


# ============================================================================
# Template Expansion
# ============================================================================

def _build_template(repo: str, metadata: dict, admin_override: dict = None) -> dict:
    """Build a full template dict from repo + fetched metadata + optional admin overrides.

    Priority for display_name / description:
      1. Admin-configured value (from Settings DB entry) — if non-empty
      2. template.yaml value (from GitHub) — if available
      3. Repo name fallback
    """
    override = admin_override or {}

    display_name = (
        override.get("display_name")
        or metadata.get("display_name")
        or metadata.get("name")
        or repo.split("/")[-1]
    )
    description = (
        override.get("description")
        or metadata.get("description", "")
    )

    return {
        "id": f"github:{repo}",
        "display_name": display_name,
        "description": description,
        "github_repo": repo,
        "github_credential_id": GITHUB_PAT_CREDENTIAL_ID,
        "source": "github",
        "resources": metadata.get("resources", {"cpu": "2", "memory": "4g"}),
        "skills": metadata.get("skills", []),
        "mcp_servers": metadata.get("mcp_servers", []),
        "required_credentials": metadata.get("required_credentials", []),
    }


# ============================================================================
# Public API
# ============================================================================

def get_all_templates() -> List[dict]:
    """Return the full resolved template list (DB-configured or defaults).

    Fetches metadata from GitHub for each repo (cached).
    """
    from services.settings_service import get_github_templates

    db_entries = get_github_templates()

    if db_entries is not None:
        # Admin-configured list
        repos = [e["github_repo"] for e in db_entries]
        all_metadata = _fetch_all_metadata(repos)
        return [
            _build_template(e["github_repo"], all_metadata.get(e["github_repo"], {}), e)
            for e in db_entries
        ]
    else:
        # Defaults
        all_metadata = _fetch_all_metadata(DEFAULT_GITHUB_TEMPLATE_REPOS)
        return [
            _build_template(repo, all_metadata.get(repo, {}))
            for repo in DEFAULT_GITHUB_TEMPLATE_REPOS
        ]


def get_github_template(template_id: str) -> Optional[dict]:
    """Get a single GitHub template by ID (e.g., 'github:owner/repo').

    Resolves metadata from GitHub (cached).
    """
    if not template_id.startswith("github:"):
        return None

    repo = template_id[len("github:"):]

    # Check if it's in the configured list (DB or defaults)
    from services.settings_service import get_github_templates
    db_entries = get_github_templates()

    if db_entries is not None:
        for entry in db_entries:
            if entry["github_repo"] == repo:
                metadata = _get_cached_metadata(repo)
                return _build_template(repo, metadata, entry)

    # Check defaults
    if repo in DEFAULT_GITHUB_TEMPLATE_REPOS:
        metadata = _get_cached_metadata(repo)
        return _build_template(repo, metadata)

    # Dynamic: repo not in any configured list but still a valid github: ID
    metadata = _get_cached_metadata(repo)
    return _build_template(repo, metadata)


def clone_github_repo(github_repo: str, github_pat: str, dest_path: Path, branch: str = None) -> bool:
    """
    Clone a GitHub repository using a Personal Access Token.

    Args:
        github_repo: Repository in format 'org/repo' (e.g., 'Abilityai/agent-ruby')
        github_pat: GitHub Personal Access Token
        dest_path: Destination path to clone to
        branch: Optional branch to clone (default: repo's default branch)

    Returns:
        True if successful, False otherwise
    """
    clone_url = f"https://oauth2:{github_pat}@github.com/{github_repo}.git"

    # Build git clone command
    clone_cmd = ["git", "clone", "--depth", "1"]
    if branch:
        clone_cmd.extend(["-b", branch])
    clone_cmd.extend([clone_url, str(dest_path)])

    try:
        result = subprocess.run(
            clone_cmd,
            capture_output=True,
            text=True,
            timeout=120
        )

        if result.returncode != 0:
            print(f"Git clone failed: {result.stderr}")
            return False

        # Remove .git directory to prevent accidental pushes from container
        git_dir = dest_path / ".git"
        if git_dir.exists():
            shutil.rmtree(git_dir)

        print(f"Successfully cloned {github_repo} to {dest_path}")
        return True

    except subprocess.TimeoutExpired:
        print(f"Git clone timed out for {github_repo}")
        return False
    except Exception as e:
        print(f"Error cloning {github_repo}: {e}")
        return False


def extract_env_vars_from_mcp_json(file_path: Path) -> Dict[str, List[str]]:
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
        print(f"Warning: Could not parse {file_path}: {e}")
        return {}

    pattern = r'\$\{([A-Z][A-Z0-9_]*)\}'
    result = {}
    mcp_servers = data.get("mcpServers", {})

    for server_name, server_config in mcp_servers.items():
        vars_for_server = set()

        if "env" in server_config:
            for key, value in server_config["env"].items():
                if isinstance(value, str):
                    matches = re.findall(pattern, value)
                    vars_for_server.update(matches)

        if "args" in server_config:
            for arg in server_config["args"]:
                if isinstance(arg, str):
                    matches = re.findall(pattern, arg)
                    vars_for_server.update(matches)

        if vars_for_server:
            result[server_name] = sorted(vars_for_server)

    return result


def extract_credentials_from_template_yaml(file_path: Path) -> Dict:
    """Extract credentials section from template.yaml."""
    if not file_path.exists():
        return {}

    try:
        with open(file_path) as f:
            data = yaml.safe_load(f)
    except Exception as e:
        print(f"Warning: Could not parse {file_path}: {e}")
        return {}

    return data.get("credentials", {})


def extract_credentials_from_env_example(file_path: Path) -> List[str]:
    """Extract variable names from .env.example."""
    if not file_path.exists():
        return []

    vars = []
    try:
        with open(file_path) as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                if '=' in line:
                    var_name = line.split('=')[0].strip()
                    if var_name and re.match(r'^[A-Z][A-Z0-9_]*$', var_name):
                        vars.append(var_name)
    except IOError as e:
        print(f"Warning: Could not read {file_path}: {e}")

    return vars


def extract_agent_credentials(repo_path: Path) -> Dict:
    """
    Extract all credential requirements from an agent repository.

    Returns:
        {
            "required_credentials": [
                {"name": "HEYGEN_API_KEY", "source": "mcp:heygen"},
                ...
            ],
            "mcp_servers": {
                "heygen": ["HEYGEN_API_KEY"],
                ...
            },
            "env_file_vars": ["BLOTATO_API_KEY", ...]
        }
    """
    result = {
        "required_credentials": [],
        "mcp_servers": {},
        "env_file_vars": []
    }

    all_vars = {}

    # Check .mcp.json or .mcp.json.template
    mcp_json = repo_path / ".mcp.json"
    mcp_template = repo_path / ".mcp.json.template"

    if mcp_json.exists():
        mcp_servers = extract_env_vars_from_mcp_json(mcp_json)
    elif mcp_template.exists():
        mcp_servers = extract_env_vars_from_mcp_json(mcp_template)
    else:
        mcp_servers = {}

    result["mcp_servers"] = mcp_servers

    for server_name, vars in mcp_servers.items():
        for var in vars:
            if var not in all_vars:
                all_vars[var] = []
            all_vars[var].append(f"mcp:{server_name}")

    # Check template.yaml
    template_yaml = repo_path / "template.yaml"
    if template_yaml.exists():
        template_creds = extract_credentials_from_template_yaml(template_yaml)

        for server_name, server_config in template_creds.get("mcp_servers", {}).items():
            env_vars = server_config.get("env_vars", [])
            for var in env_vars:
                if var not in all_vars:
                    all_vars[var] = []
                if f"mcp:{server_name}" not in all_vars[var]:
                    all_vars[var].append(f"template:mcp:{server_name}")

        env_file_vars = template_creds.get("env_file", [])
        result["env_file_vars"] = env_file_vars
        for var in env_file_vars:
            if var not in all_vars:
                all_vars[var] = []
            all_vars[var].append("template:env_file")

    # Check .env.example
    env_example = repo_path / ".env.example"
    if env_example.exists():
        env_vars = extract_credentials_from_env_example(env_example)
        for var in env_vars:
            if var not in all_vars:
                all_vars[var] = []
            all_vars[var].append(".env.example")

    # Build consolidated list
    for var_name in sorted(all_vars.keys()):
        sources = all_vars[var_name]
        primary_source = sources[0] if sources else "unknown"
        result["required_credentials"].append({
            "name": var_name,
            "source": primary_source
        })

    return result


def generate_credential_files(
    template_data: dict,
    agent_credentials: dict,
    agent_name: str,
    template_base_path: Optional[Path] = None
) -> dict:
    """
    Generate credential files (.mcp.json, .env, config files) with real values.
    Returns dict of {filepath: content} to write into container.
    """
    files = {}
    creds_schema = template_data.get("credentials", {})

    # Generate .mcp.json with real credentials
    mcp_servers_schema = creds_schema.get("mcp_servers", {})
    if mcp_servers_schema:
        if template_base_path:
            mcp_template_path = template_base_path / ".mcp.json"
        else:
            templates_dir = Path("/agent-configs/templates")
            if not templates_dir.exists():
                templates_dir = Path("./config/agent-templates")
            template_name = template_data.get("name", "")
            mcp_template_path = templates_dir / template_name / ".mcp.json"

        if mcp_template_path.exists():
            with open(mcp_template_path) as f:
                mcp_config = json.load(f)

            for server_name, server_config in mcp_config.get("mcpServers", {}).items():
                if "env" in server_config:
                    for env_key, env_val in server_config["env"].items():
                        if isinstance(env_val, str) and env_val.startswith("${") and env_val.endswith("}"):
                            var_name = env_val[2:-1]
                            real_value = agent_credentials.get(var_name, "")
                            server_config["env"][env_key] = real_value

                if "args" in server_config:
                    new_args = []
                    for arg in server_config["args"]:
                        if isinstance(arg, str) and arg.startswith("${") and arg.endswith("}"):
                            var_name = arg[2:-1]
                            real_value = agent_credentials.get(var_name, "")
                            new_args.append(real_value)
                        else:
                            new_args.append(arg)
                    server_config["args"] = new_args

            files[".mcp.json"] = json.dumps(mcp_config, indent=2)

    # Generate .env file
    env_vars = creds_schema.get("env_file", [])
    if env_vars:
        env_lines = ["# Generated by Trinity - Agent credentials", ""]
        for var_name in env_vars:
            value = agent_credentials.get(var_name, "")
            env_lines.append(f"{var_name}={value}")
        files[".env"] = "\n".join(env_lines)

    # Generate config files from templates
    config_files = creds_schema.get("config_files", [])
    for config_file in config_files:
        file_path = config_file.get("path", "")
        template_content = config_file.get("template", "")

        if file_path and template_content:
            content = template_content
            for var_name, value in agent_credentials.items():
                content = content.replace(f"{{{var_name}}}", str(value))
            files[file_path] = content

    return files


# ============================================================================
# Trinity-Compatible Validation (Local Agent Deployment)
# ============================================================================

from typing import Tuple


def is_trinity_compatible(path: Path) -> Tuple[bool, Optional[str], Optional[dict]]:
    """
    Check if a directory contains a Trinity-compatible agent.

    A Trinity-compatible agent must have:
    1. template.yaml file
    2. name field in template.yaml
    3. resources field in template.yaml

    Args:
        path: Path to the agent directory

    Returns:
        Tuple of (is_compatible, error_message, template_data)
        - is_compatible: True if the agent is Trinity-compatible
        - error_message: Description of why validation failed (None if valid)
        - template_data: Parsed template.yaml data (None if invalid)
    """
    template_path = path / "template.yaml"

    if not template_path.exists():
        return (False, "Missing template.yaml", None)

    try:
        with open(template_path) as f:
            template_data = yaml.safe_load(f)
    except Exception as e:
        return (False, f"Invalid template.yaml: {e}", None)

    if not template_data:
        return (False, "template.yaml is empty", None)

    if not template_data.get("name"):
        return (False, "template.yaml missing required field: name", None)

    if not template_data.get("resources"):
        return (False, "template.yaml missing required field: resources", None)

    # Validate resources has expected structure
    resources = template_data.get("resources", {})
    if not isinstance(resources, dict):
        return (False, "template.yaml resources must be a dictionary", None)

    # Check for CLAUDE.md (warn but don't fail)
    claude_md = path / "CLAUDE.md"
    if not claude_md.exists():
        # This is a warning, not an error - we still allow deployment
        print(f"Warning: {path} does not contain CLAUDE.md (recommended)")

    return (True, None, template_data)


def get_name_from_template(path: Path) -> Optional[str]:
    """
    Extract agent name from template.yaml.

    Args:
        path: Path to the agent directory

    Returns:
        Agent name from template.yaml, or None if not found
    """
    template_path = path / "template.yaml"
    if not template_path.exists():
        return None

    try:
        with open(template_path) as f:
            template_data = yaml.safe_load(f)
            return template_data.get("name") if template_data else None
    except Exception:
        return None
