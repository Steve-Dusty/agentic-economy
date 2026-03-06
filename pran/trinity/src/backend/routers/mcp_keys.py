"""
MCP API Key management routes for the Trinity backend.
"""
from typing import List
from fastapi import APIRouter, Depends, HTTPException, Request

from models import User
from database import db, McpApiKeyCreate, McpApiKey, McpApiKeyWithSecret
from dependencies import get_current_user

router = APIRouter(prefix="/api/mcp", tags=["mcp"])


@router.post("/keys", response_model=McpApiKeyWithSecret)
async def create_mcp_api_key_endpoint(
    key_data: McpApiKeyCreate,
    request: Request,
    current_user: User = Depends(get_current_user)
):
    """
    Create a new MCP API key for the current user.
    The full API key is only returned once during creation - store it securely.
    """
    try:
        api_key = db.create_mcp_api_key(current_user.username, key_data)

        if not api_key:
            raise HTTPException(status_code=400, detail="Failed to create API key")

        return api_key
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create MCP API key: {str(e)}")


@router.get("/keys", response_model=List[McpApiKey])
async def list_mcp_api_keys_endpoint(
    request: Request,
    current_user: User = Depends(get_current_user)
):
    """List all MCP API keys for the current user."""
    try:
        if current_user.role == "admin":
            keys = db.list_all_mcp_api_keys()
        else:
            keys = db.list_mcp_api_keys(current_user.username)

        return keys
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list MCP API keys: {str(e)}")


@router.post("/keys/ensure-default", response_model=McpApiKeyWithSecret | None)
async def ensure_default_mcp_api_key(
    request: Request,
    current_user: User = Depends(get_current_user)
):
    """
    Ensure the user has at least one user-scoped MCP API key.
    If no user-scoped keys exist, creates a default one and returns it.

    This is used for first-time setup to provide users with a ready-to-use
    MCP configuration.

    Returns:
        - The newly created key (with full api_key) if one was created
        - None if the user already has a user-scoped key
    """
    try:
        # Check if user has any user-scoped keys
        keys = db.list_mcp_api_keys(current_user.username)
        user_keys = [k for k in keys if k.scope == "user" and k.is_active]

        if user_keys:
            # User already has a key, no need to create
            return None

        # Create a default key
        from database import McpApiKeyCreate
        key_data = McpApiKeyCreate(
            name="Default MCP Key",
            description="Auto-generated key for MCP access"
        )

        api_key = db.create_mcp_api_key(current_user.username, key_data)

        if not api_key:
            raise HTTPException(status_code=400, detail="Failed to create default API key")

        return api_key

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to ensure default MCP API key: {str(e)}")


@router.get("/keys/{key_id}", response_model=McpApiKey)
async def get_mcp_api_key_endpoint(
    key_id: str,
    request: Request,
    current_user: User = Depends(get_current_user)
):
    """Get details of a specific MCP API key."""
    key = db.get_mcp_api_key(key_id, current_user.username)

    if not key:
        raise HTTPException(status_code=404, detail="MCP API key not found")

    return key


@router.post("/keys/{key_id}/revoke")
async def revoke_mcp_api_key_endpoint(
    key_id: str,
    request: Request,
    current_user: User = Depends(get_current_user)
):
    """Revoke (deactivate) an MCP API key."""
    success = db.revoke_mcp_api_key(key_id, current_user.username)

    if not success:
        raise HTTPException(status_code=404, detail="MCP API key not found")

    return {"message": f"MCP API key {key_id} revoked"}


@router.delete("/keys/{key_id}")
async def delete_mcp_api_key_endpoint(
    key_id: str,
    request: Request,
    current_user: User = Depends(get_current_user)
):
    """Permanently delete an MCP API key."""
    success = db.delete_mcp_api_key(key_id, current_user.username)

    if not success:
        raise HTTPException(status_code=404, detail="MCP API key not found")

    return {"message": f"MCP API key {key_id} deleted"}


@router.post("/validate")
async def validate_mcp_api_key_http_endpoint(request: Request):
    """
    Validate an MCP API key (called by the MCP server).
    Accepts the API key in the Authorization header as 'Bearer <key>'.
    This endpoint is NOT protected by JWT - it validates MCP API keys.

    Returns:
        - valid: True if key is valid
        - user_id: Username of the key owner
        - user_email: Email of the key owner
        - key_name: Name of the API key
        - agent_name: Agent name if scope is 'agent' (for agent-to-agent auth)
        - scope: 'user' or 'agent'
    """
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(
            status_code=401,
            detail="Missing or invalid Authorization header"
        )

    api_key = auth_header[7:]  # Remove "Bearer " prefix

    result = db.validate_mcp_api_key(api_key)

    if not result:
        raise HTTPException(status_code=401, detail="Invalid or inactive API key")

    return {
        "valid": True,
        "key_id": result.get("key_id"),  # MCP API key ID (AUDIT-001)
        "user_id": result.get("user_id"),
        "user_email": result.get("user_email"),
        "key_name": result.get("key_name"),
        "agent_name": result.get("agent_name"),  # Agent-to-agent collaboration
        "scope": result.get("scope", "user")  # 'user' or 'agent'
    }
