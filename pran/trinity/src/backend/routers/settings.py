"""
System settings routes for the Trinity backend.

Provides endpoints for managing system-wide configuration like the Trinity prompt.
Admin-only access for modification, read access for all authenticated users.
"""
import os
import re
import httpx
from typing import List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from models import User
from database import db, SystemSetting, SystemSettingUpdate
from dependencies import get_current_user

# Import from settings_service (these are re-exported for backward compatibility)
from services.settings_service import (
    get_anthropic_api_key,
    get_github_pat,
    get_google_api_key,
    get_ops_setting,
    settings_service,
    OPS_SETTINGS_DEFAULTS,
    OPS_SETTINGS_DESCRIPTIONS,
)

router = APIRouter(prefix="/api/settings", tags=["settings"])


# ============================================================================
# API Keys Management - Helper Functions and Models
# ============================================================================

class ApiKeyUpdate(BaseModel):
    """Request body for updating an API key."""
    api_key: str


class ApiKeyTest(BaseModel):
    """Request body for testing an API key."""
    api_key: str


# Note: get_anthropic_api_key and get_github_pat are now imported from
# services.settings_service for proper architecture (services shouldn't import from routers)


def mask_api_key(key: str) -> str:
    """Mask an API key for display, showing only last 4 characters."""
    if not key or len(key) < 8:
        return "****"
    return f"...{key[-4:]}"


# ============================================================================
# Ops Settings Configuration
# ============================================================================

# Note: OPS_SETTINGS_DEFAULTS and OPS_SETTINGS_DESCRIPTIONS are now imported from
# services.settings_service for proper architecture


class OpsSettingsUpdate(BaseModel):
    """Request body for updating ops settings."""
    settings: Dict[str, str]


def require_admin(current_user: User):
    """Verify user is an admin."""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")


@router.get("", response_model=List[SystemSetting])
async def get_all_settings(
    request: Request,
    current_user: User = Depends(get_current_user)
):
    """
    Get all system settings.

    Admin-only endpoint to view all configuration values.
    """
    require_admin(current_user)

    try:
        settings = db.get_all_settings()

        return settings
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get settings: {str(e)}")


# ============================================================================
# API Keys Management Endpoints
# NOTE: These routes MUST be defined BEFORE the /{key} catch-all route
# ============================================================================

@router.get("/api-keys")
async def get_api_keys_status(
    request: Request,
    current_user: User = Depends(get_current_user)
):
    """
    Get status of configured API keys.

    Admin-only. Returns masked key info for security.
    """
    require_admin(current_user)

    try:
        # Get Anthropic key
        anthropic_key = get_anthropic_api_key()
        anthropic_configured = bool(anthropic_key)

        # Check if it's from settings or env
        key_from_settings = bool(db.get_setting_value('anthropic_api_key', None))

        # Get GitHub PAT
        github_pat = get_github_pat()
        github_configured = bool(github_pat)
        github_from_settings = bool(db.get_setting_value('github_pat', None))

        return {
            "anthropic": {
                "configured": anthropic_configured,
                "masked": mask_api_key(anthropic_key) if anthropic_configured else None,
                "source": "settings" if key_from_settings else ("env" if anthropic_configured else None)
            },
            "github": {
                "configured": github_configured,
                "masked": mask_api_key(github_pat) if github_configured else None,
                "source": "settings" if github_from_settings else ("env" if github_configured else None)
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get API keys status: {str(e)}")


@router.put("/api-keys/anthropic")
async def update_anthropic_key(
    body: ApiKeyUpdate,
    request: Request,
    current_user: User = Depends(get_current_user)
):
    """
    Set or update the Anthropic API key.

    Admin-only. Key is stored in system settings.
    """
    require_admin(current_user)

    try:
        # Validate format
        key = body.api_key.strip()
        if not key.startswith('sk-ant-'):
            raise HTTPException(
                status_code=400,
                detail="Invalid API key format. Anthropic keys start with 'sk-ant-'"
            )

        # Store in settings
        db.set_setting('anthropic_api_key', key)

        return {
            "success": True,
            "masked": mask_api_key(key)
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update API key: {str(e)}")


@router.delete("/api-keys/anthropic")
async def delete_anthropic_key(
    request: Request,
    current_user: User = Depends(get_current_user)
):
    """
    Delete the Anthropic API key from settings.

    Admin-only. Will fall back to env var if configured.
    """
    require_admin(current_user)

    try:
        deleted = db.delete_setting('anthropic_api_key')

        # Check if env var fallback exists
        env_key = os.getenv('ANTHROPIC_API_KEY', '')

        return {
            "success": True,
            "deleted": deleted,
            "fallback_configured": bool(env_key)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete API key: {str(e)}")


@router.post("/api-keys/anthropic/test")
async def test_anthropic_key(
    body: ApiKeyTest,
    request: Request,
    current_user: User = Depends(get_current_user)
):
    """
    Test if an Anthropic API key is valid.

    Admin-only. Makes a lightweight API call to validate the key.
    """
    require_admin(current_user)

    try:
        key = body.api_key.strip()

        # Validate format first
        if not key.startswith('sk-ant-'):
            return {
                "valid": False,
                "error": "Invalid format. Anthropic keys start with 'sk-ant-'"
            }

        # Make a lightweight API call to test the key
        # Using the models endpoint which is simple and doesn't create any resources
        async with httpx.AsyncClient() as client:
            response = await client.get(
                "https://api.anthropic.com/v1/models",
                headers={
                    "x-api-key": key,
                    "anthropic-version": "2023-06-01"
                },
                timeout=10.0
            )

            if response.status_code == 200:
                return {"valid": True}
            elif response.status_code == 401:
                return {
                    "valid": False,
                    "error": "Invalid API key"
                }
            else:
                return {
                    "valid": False,
                    "error": f"API returned status {response.status_code}"
                }

    except httpx.TimeoutException:
        return {
            "valid": False,
            "error": "Request timed out. Please try again."
        }
    except Exception as e:
        return {
            "valid": False,
            "error": f"Error testing key: {str(e)}"
        }


@router.put("/api-keys/github")
async def update_github_pat(
    body: ApiKeyUpdate,
    request: Request,
    current_user: User = Depends(get_current_user)
):
    """
    Set or update the GitHub Personal Access Token.

    Admin-only. Token is stored in system settings.
    """
    require_admin(current_user)

    try:
        # Validate format
        key = body.api_key.strip()
        if not (key.startswith('ghp_') or key.startswith('github_pat_')):
            raise HTTPException(
                status_code=400,
                detail="Invalid token format. GitHub PATs start with 'ghp_' or 'github_pat_'"
            )

        # Store in settings
        db.set_setting('github_pat', key)

        return {
            "success": True,
            "masked": mask_api_key(key)
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update GitHub PAT: {str(e)}")


@router.delete("/api-keys/github")
async def delete_github_pat(
    request: Request,
    current_user: User = Depends(get_current_user)
):
    """
    Delete the GitHub PAT from settings.

    Admin-only. Will fall back to env var if configured.
    """
    require_admin(current_user)

    try:
        deleted = db.delete_setting('github_pat')

        # Check if env var fallback exists
        env_key = os.getenv('GITHUB_PAT', '')

        return {
            "success": True,
            "deleted": deleted,
            "fallback_configured": bool(env_key)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete GitHub PAT: {str(e)}")


@router.post("/api-keys/github/test")
async def test_github_pat(
    body: ApiKeyTest,
    request: Request,
    current_user: User = Depends(get_current_user)
):
    """
    Test if a GitHub PAT is valid.

    Admin-only. Makes a lightweight API call to validate the token.
    """
    require_admin(current_user)

    try:
        key = body.api_key.strip()

        # Validate format first
        if not (key.startswith('ghp_') or key.startswith('github_pat_')):
            return {
                "valid": False,
                "error": "Invalid format. GitHub PATs start with 'ghp_' or 'github_pat_'"
            }

        # Make a lightweight API call to test the token
        # Using the user endpoint which is simple and doesn't create any resources
        async with httpx.AsyncClient() as client:
            response = await client.get(
                "https://api.github.com/user",
                headers={
                    "Authorization": f"Bearer {key}",
                    "Accept": "application/vnd.github+json",
                    "X-GitHub-Api-Version": "2022-11-28"
                },
                timeout=10.0
            )

            if response.status_code == 200:
                data = response.json()

                # Determine token type and check permissions
                is_fine_grained = key.startswith('github_pat_')
                scopes = []
                has_repo_access = False

                if is_fine_grained:
                    # Fine-grained PATs: Test actual permissions by trying to list repos
                    # This will succeed if the token has proper permissions
                    try:
                        repos_response = await client.get(
                            "https://api.github.com/user/repos",
                            headers={
                                "Authorization": f"Bearer {key}",
                                "Accept": "application/vnd.github+json",
                                "X-GitHub-Api-Version": "2022-11-28"
                            },
                            params={"per_page": 1},  # Just test access, don't fetch all repos
                            timeout=10.0
                        )
                        # If we can list repos, the token has sufficient permissions
                        has_repo_access = repos_response.status_code == 200
                        scopes = ["fine-grained-pat"]
                    except Exception:
                        has_repo_access = False
                        scopes = ["fine-grained-pat"]
                else:
                    # Classic PAT: Check X-OAuth-Scopes header
                    scope_header = response.headers.get("X-OAuth-Scopes", "")
                    scopes = [s.strip() for s in scope_header.split(",") if s.strip()]
                    has_repo_access = "repo" in scopes or "public_repo" in scopes

                return {
                    "valid": True,
                    "username": data.get("login"),
                    "scopes": scopes,
                    "token_type": "fine-grained" if is_fine_grained else "classic",
                    "has_repo_access": has_repo_access
                }
            elif response.status_code == 401:
                return {
                    "valid": False,
                    "error": "Invalid Personal Access Token"
                }
            else:
                return {
                    "valid": False,
                    "error": f"GitHub API returned status {response.status_code}"
                }

    except httpx.TimeoutException:
        return {
            "valid": False,
            "error": "Request timed out. Please try again."
        }
    except Exception as e:
        return {
            "valid": False,
            "error": f"Error testing token: {str(e)}"
        }


# ============================================================================
# Slack Integration Settings (SLACK-001)
# ============================================================================

@router.get("/slack")
async def get_slack_settings_status(
    request: Request,
    current_user: User = Depends(get_current_user)
):
    """
    Get status of Slack integration settings.

    Admin-only. Returns masked key info for security.
    """
    require_admin(current_user)

    try:
        from services.settings_service import (
            get_slack_client_id,
            get_slack_client_secret,
            get_slack_signing_secret,
        )

        client_id = get_slack_client_id()
        client_secret = get_slack_client_secret()
        signing_secret = get_slack_signing_secret()

        # Check sources
        client_id_from_settings = bool(db.get_setting_value('slack_client_id', None))
        client_secret_from_settings = bool(db.get_setting_value('slack_client_secret', None))
        signing_secret_from_settings = bool(db.get_setting_value('slack_signing_secret', None))

        return {
            "configured": bool(client_id and client_secret and signing_secret),
            "client_id": {
                "configured": bool(client_id),
                "masked": mask_api_key(client_id) if client_id else None,
                "source": "settings" if client_id_from_settings else ("env" if client_id else None)
            },
            "client_secret": {
                "configured": bool(client_secret),
                "masked": mask_api_key(client_secret) if client_secret else None,
                "source": "settings" if client_secret_from_settings else ("env" if client_secret else None)
            },
            "signing_secret": {
                "configured": bool(signing_secret),
                "masked": mask_api_key(signing_secret) if signing_secret else None,
                "source": "settings" if signing_secret_from_settings else ("env" if signing_secret else None)
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get Slack settings: {str(e)}")


class SlackSettingsUpdate(BaseModel):
    """Request body for updating Slack settings."""
    client_id: str = None
    client_secret: str = None
    signing_secret: str = None


@router.put("/slack")
async def update_slack_settings(
    body: SlackSettingsUpdate,
    request: Request,
    current_user: User = Depends(get_current_user)
):
    """
    Update Slack integration settings.

    Admin-only. All fields are optional - only provided values are updated.
    """
    require_admin(current_user)

    try:
        updated = []

        if body.client_id is not None:
            db.set_setting('slack_client_id', body.client_id.strip())
            updated.append('client_id')

        if body.client_secret is not None:
            db.set_setting('slack_client_secret', body.client_secret.strip())
            updated.append('client_secret')

        if body.signing_secret is not None:
            db.set_setting('slack_signing_secret', body.signing_secret.strip())
            updated.append('signing_secret')

        return {
            "success": True,
            "updated": updated
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update Slack settings: {str(e)}")


@router.delete("/slack")
async def delete_slack_settings(
    request: Request,
    current_user: User = Depends(get_current_user)
):
    """
    Delete all Slack settings from database.

    Admin-only. Will fall back to env vars if configured.
    """
    require_admin(current_user)

    try:
        deleted = []
        for key in ['slack_client_id', 'slack_client_secret', 'slack_signing_secret']:
            if db.delete_setting(key):
                deleted.append(key)

        # Check env var fallbacks
        import os
        fallback_configured = bool(
            os.getenv('SLACK_CLIENT_ID') and
            os.getenv('SLACK_CLIENT_SECRET') and
            os.getenv('SLACK_SIGNING_SECRET')
        )

        return {
            "success": True,
            "deleted": deleted,
            "fallback_configured": fallback_configured
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete Slack settings: {str(e)}")


# ============================================================================
# Email Whitelist Management (Phase 12.4)
# ============================================================================

@router.get("/email-whitelist")
async def list_email_whitelist(
    request: Request,
    current_user: User = Depends(get_current_user)
):
    """
    List all whitelisted emails.

    Admin-only endpoint.
    """
    require_admin(current_user)

    whitelist = db.list_whitelist(limit=1000)

    return {"whitelist": whitelist}


@router.post("/email-whitelist")
async def add_email_to_whitelist(
    request: Request,
    current_user: User = Depends(get_current_user)
):
    """
    Add an email to the whitelist.

    Admin-only endpoint.
    """
    from database import EmailWhitelistAdd

    require_admin(current_user)

    # Parse request
    body = await request.json()
    add_request = EmailWhitelistAdd(**body)
    email = add_request.email.lower()

    # Add to whitelist
    try:
        added = db.add_to_whitelist(email, current_user.username, source=add_request.source)

        if not added:
            raise HTTPException(
                status_code=409,
                detail=f"Email {email} is already whitelisted"
            )

        return {"success": True, "email": email}

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/email-whitelist/{email}")
async def remove_email_from_whitelist(
    email: str,
    request: Request,
    current_user: User = Depends(get_current_user)
):
    """
    Remove an email from the whitelist.

    Admin-only endpoint.
    """
    require_admin(current_user)

    # Remove from whitelist
    removed = db.remove_from_whitelist(email)

    if not removed:
        raise HTTPException(
            status_code=404,
            detail=f"Email {email} not found in whitelist"
        )

    return {"success": True, "email": email}

# ============================================================================
# GitHub Templates Configuration (TMPL-001)
# ============================================================================

class GitHubTemplateEntry(BaseModel):
    """A single GitHub template entry."""
    github_repo: str
    display_name: str = ""
    description: str = ""


class GitHubTemplatesUpdate(BaseModel):
    """Request body for updating GitHub templates."""
    templates: List[GitHubTemplateEntry]


_REPO_PATTERN = re.compile(r'^[a-zA-Z0-9._-]+/[a-zA-Z0-9._-]+$')


@router.get("/github-templates")
async def get_github_templates(
    request: Request,
    current_user: User = Depends(get_current_user)
):
    """
    Get configured GitHub templates.

    Admin-only. Returns the configured list or the hardcoded defaults.
    Display names and descriptions are resolved from each repo's template.yaml.
    """
    require_admin(current_user)

    from config import DEFAULT_GITHUB_TEMPLATE_REPOS
    from services.template_service import _fetch_all_metadata

    db_templates = settings_service.get_github_templates()
    if db_templates is not None:
        repos = [e["github_repo"] for e in db_templates]
        all_metadata = _fetch_all_metadata(repos)
        enriched = []
        for entry in db_templates:
            repo = entry["github_repo"]
            meta = all_metadata.get(repo, {})
            admin_name = entry.get("display_name", "")
            admin_desc = entry.get("description", "")
            enriched.append({
                "github_repo": repo,
                "display_name": admin_name,
                "description": admin_desc,
                "resolved_name": admin_name or meta.get("display_name") or meta.get("name") or repo.split("/")[-1],
                "resolved_description": admin_desc or meta.get("description", ""),
            })
        return {
            "source": "settings",
            "templates": enriched
        }
    else:
        all_metadata = _fetch_all_metadata(DEFAULT_GITHUB_TEMPLATE_REPOS)
        defaults = []
        for repo in DEFAULT_GITHUB_TEMPLATE_REPOS:
            meta = all_metadata.get(repo, {})
            defaults.append({
                "github_repo": repo,
                "display_name": "",
                "description": "",
                "resolved_name": meta.get("display_name") or meta.get("name") or repo.split("/")[-1],
                "resolved_description": meta.get("description", ""),
            })
        return {
            "source": "defaults",
            "templates": defaults
        }


@router.put("/github-templates")
async def update_github_templates(
    body: GitHubTemplatesUpdate,
    request: Request,
    current_user: User = Depends(get_current_user)
):
    """
    Set the GitHub templates list.

    Admin-only. Validates owner/repo format for each entry.
    """
    require_admin(current_user)

    # Validate each entry
    for entry in body.templates:
        if not _REPO_PATTERN.match(entry.github_repo):
            raise HTTPException(
                status_code=400,
                detail=f"Invalid repository format: '{entry.github_repo}'. Expected 'owner/repo'."
            )

    # Convert to list of dicts for storage
    templates_data = [entry.model_dump() for entry in body.templates]
    settings_service.set_github_templates(templates_data)

    return {
        "success": True,
        "count": len(templates_data)
    }


@router.delete("/github-templates")
async def delete_github_templates(
    request: Request,
    current_user: User = Depends(get_current_user)
):
    """
    Reset GitHub templates to hardcoded defaults.

    Admin-only. Removes the DB override so the system falls back to config.py defaults.
    """
    require_admin(current_user)

    deleted = settings_service.delete_github_templates()

    return {
        "success": True,
        "deleted": deleted,
        "message": "GitHub templates reset to defaults"
    }


# ============================================================================
# Generic Settings CRUD - /{key} catch-all routes
# NOTE: These must come AFTER specific routes like /api-keys
# ============================================================================

@router.get("/{key}")
async def get_setting(
    key: str,
    request: Request,
    current_user: User = Depends(get_current_user)
):
    """
    Get a specific setting by key.

    Returns the setting value or 404 if not found.
    Admin-only for most settings.
    """
    require_admin(current_user)

    try:
        setting = db.get_setting(key)

        if not setting:
            raise HTTPException(status_code=404, detail=f"Setting '{key}' not found")

        return setting
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get setting: {str(e)}")


@router.put("/{key}", response_model=SystemSetting)
async def update_setting(
    key: str,
    body: SystemSettingUpdate,
    request: Request,
    current_user: User = Depends(get_current_user)
):
    """
    Create or update a system setting.

    Admin-only endpoint. Creates the setting if it doesn't exist.
    """
    require_admin(current_user)

    try:
        setting = db.set_setting(key, body.value)

        return setting
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update setting: {str(e)}")


@router.delete("/{key}")
async def delete_setting(
    key: str,
    request: Request,
    current_user: User = Depends(get_current_user)
):
    """
    Delete a system setting.

    Admin-only endpoint. Returns success even if setting didn't exist.
    """
    require_admin(current_user)

    try:
        deleted = db.delete_setting(key)

        return {"success": True, "deleted": deleted}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete setting: {str(e)}")


# ============================================================================
# Ops Settings Endpoints
# ============================================================================

@router.get("/ops/config")
async def get_ops_settings(
    request: Request,
    current_user: User = Depends(get_current_user)
):
    """
    Get all ops-related settings with their current values and defaults.

    Admin-only. Returns both stored values and defaults for ops settings.
    Useful for displaying the ops configuration panel.
    """
    require_admin(current_user)

    try:
        # Get current values from database
        all_settings = db.get_settings_dict()

        # Build response with defaults and current values
        ops_config = {}
        for key, default_value in OPS_SETTINGS_DEFAULTS.items():
            current_value = all_settings.get(key, default_value)
            ops_config[key] = {
                "value": current_value,
                "default": default_value,
                "description": OPS_SETTINGS_DESCRIPTIONS.get(key, ""),
                "is_default": current_value == default_value
            }

        return {
            "settings": ops_config
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get ops settings: {str(e)}")


@router.put("/ops/config")
async def update_ops_settings(
    body: OpsSettingsUpdate,
    request: Request,
    current_user: User = Depends(get_current_user)
):
    """
    Update multiple ops settings at once.

    Admin-only. Only accepts valid ops setting keys.
    Invalid keys are ignored with a warning.
    """
    require_admin(current_user)

    try:
        updated = []
        ignored = []

        for key, value in body.settings.items():
            if key in OPS_SETTINGS_DEFAULTS:
                db.set_setting(key, value)
                updated.append(key)
            else:
                ignored.append(key)

        return {
            "success": True,
            "updated": updated,
            "ignored": ignored if ignored else None
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update ops settings: {str(e)}")


@router.post("/ops/reset")
async def reset_ops_settings(
    request: Request,
    current_user: User = Depends(get_current_user)
):
    """
    Reset all ops settings to their default values.

    Admin-only. Removes all ops settings from the database,
    causing them to fall back to defaults.
    """
    require_admin(current_user)

    try:
        deleted = []
        for key in OPS_SETTINGS_DEFAULTS.keys():
            if db.delete_setting(key):
                deleted.append(key)

        return {
            "success": True,
            "message": "Ops settings reset to defaults",
            "reset": deleted
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to reset ops settings: {str(e)}")


# Note: get_ops_setting is now imported from services.settings_service


