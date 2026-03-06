"""
Agent Service Files - File browser operations.

Handles file listing, download, preview, and delete for agent workspaces.
"""
import logging

import httpx
from fastapi import HTTPException, Request
from fastapi.responses import PlainTextResponse, StreamingResponse

from models import User
from database import db
from services.docker_service import get_agent_container
from services.docker_utils import container_reload
from .helpers import agent_http_request

logger = logging.getLogger(__name__)


async def list_agent_files_logic(
    agent_name: str,
    path: str,
    current_user: User,
    request: Request,
    show_hidden: bool = False
) -> dict:
    """
    List files in the agent's workspace directory.
    Returns a flat list of files with metadata (name, size, modified date).

    Args:
        agent_name: Name of the agent
        path: Directory path to list
        current_user: Current authenticated user
        request: HTTP request object
        show_hidden: If True, include hidden files (starting with .)
    """
    if not db.can_user_access_agent(current_user.username, agent_name):
        raise HTTPException(status_code=403, detail="You don't have permission to access this agent")

    container = get_agent_container(agent_name)
    if not container:
        raise HTTPException(status_code=404, detail="Agent not found")

    await container_reload(container)
    if container.status != "running":
        raise HTTPException(status_code=400, detail="Agent must be running to browse files")

    try:
        # Call agent's internal file listing API with retry
        response = await agent_http_request(
            agent_name,
            "GET",
            "/api/files",
            params={"path": path, "show_hidden": str(show_hidden).lower()},
            max_retries=3,
            retry_delay=1.0,
            timeout=30.0
        )
        if response.status_code == 200:
            return response.json()
        else:
            raise HTTPException(
                status_code=response.status_code,
                detail=f"Failed to list files: {response.text}"
            )
    except httpx.ConnectError:
        # Agent server not ready - return 503 so tests can skip
        raise HTTPException(
            status_code=503,
            detail="Agent server not ready. The agent may still be starting up."
        )
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="File listing timed out")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list files: {str(e)}")


async def download_agent_file_logic(
    agent_name: str,
    path: str,
    current_user: User,
    request: Request
) -> PlainTextResponse:
    """
    Download a file from the agent's workspace.
    Returns the file content as plain text.
    """
    if not db.can_user_access_agent(current_user.username, agent_name):
        raise HTTPException(status_code=403, detail="You don't have permission to access this agent")

    container = get_agent_container(agent_name)
    if not container:
        raise HTTPException(status_code=404, detail="Agent not found")

    await container_reload(container)
    if container.status != "running":
        raise HTTPException(status_code=400, detail="Agent must be running to download files")

    try:
        # Call agent's internal file download API with retry
        response = await agent_http_request(
            agent_name,
            "GET",
            "/api/files/download",
            params={"path": path},
            max_retries=3,
            retry_delay=1.0,
            timeout=60.0
        )
        if response.status_code == 200:
            return PlainTextResponse(content=response.text)
        else:
            raise HTTPException(
                status_code=response.status_code,
                detail=f"Failed to download file: {response.text}"
            )
    except httpx.ConnectError:
        # Agent server not ready - return 503 so tests can skip
        raise HTTPException(
            status_code=503,
            detail="Agent server not ready. The agent may still be starting up."
        )
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="File download timed out")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to download file: {str(e)}")


async def delete_agent_file_logic(
    agent_name: str,
    path: str,
    current_user: User,
    request: Request
) -> dict:
    """
    Delete a file or directory from the agent's workspace.
    """
    if not db.can_user_access_agent(current_user.username, agent_name):
        raise HTTPException(status_code=403, detail="You don't have permission to access this agent")

    container = get_agent_container(agent_name)
    if not container:
        raise HTTPException(status_code=404, detail="Agent not found")

    await container_reload(container)
    if container.status != "running":
        raise HTTPException(status_code=400, detail="Agent must be running to delete files")

    try:
        # Call agent's internal file delete API with retry
        response = await agent_http_request(
            agent_name,
            "DELETE",
            "/api/files",
            params={"path": path},
            max_retries=3,
            retry_delay=1.0,
            timeout=30.0
        )
        if response.status_code == 200:
            result = response.json()
            return result
        else:
            raise HTTPException(
                status_code=response.status_code,
                detail=response.json().get("detail", f"Failed to delete: {response.text}")
            )
    except httpx.ConnectError:
        # Agent server not ready - return 503 so tests can skip
        raise HTTPException(
            status_code=503,
            detail="Agent server not ready. The agent may still be starting up."
        )
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="File deletion timed out")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete file: {str(e)}")


async def preview_agent_file_logic(
    agent_name: str,
    path: str,
    current_user: User,
    request: Request
) -> StreamingResponse:
    """
    Get file with proper MIME type for preview.
    Streams the response from the agent container.
    """
    if not db.can_user_access_agent(current_user.username, agent_name):
        raise HTTPException(status_code=403, detail="You don't have permission to access this agent")

    container = get_agent_container(agent_name)
    if not container:
        raise HTTPException(status_code=404, detail="Agent not found")

    await container_reload(container)
    if container.status != "running":
        raise HTTPException(status_code=400, detail="Agent must be running to preview files")

    try:
        # Call agent's internal file preview API with retry
        response = await agent_http_request(
            agent_name,
            "GET",
            "/api/files/preview",
            params={"path": path},
            max_retries=3,
            retry_delay=1.0,
            timeout=30.0
        )
        if response.status_code != 200:
            raise HTTPException(
                status_code=response.status_code,
                detail=response.json().get("detail", f"Failed to preview: {response.text}")
            )

        content_type = response.headers.get("content-type", "application/octet-stream")
        content_disposition = response.headers.get("content-disposition")

        # For small files, return directly
        return StreamingResponse(
            iter([response.content]),
            media_type=content_type,
            headers={"Content-Disposition": content_disposition} if content_disposition else {}
        )

    except httpx.ConnectError:
        # Agent server not ready - return 503 so tests can skip
        raise HTTPException(
            status_code=503,
            detail="Agent server not ready. The agent may still be starting up."
        )
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="File preview timed out")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to preview file: {str(e)}")


async def update_agent_file_logic(
    agent_name: str,
    path: str,
    content: str,
    current_user: User,
    request: Request
) -> dict:
    """
    Update a file's content in the agent's workspace.

    Args:
        agent_name: Name of the agent
        path: File path to update
        content: New file content
        current_user: Current authenticated user
        request: HTTP request object
    """
    if not db.can_user_access_agent(current_user.username, agent_name):
        raise HTTPException(status_code=403, detail="You don't have permission to access this agent")

    container = get_agent_container(agent_name)
    if not container:
        raise HTTPException(status_code=404, detail="Agent not found")

    await container_reload(container)
    if container.status != "running":
        raise HTTPException(status_code=400, detail="Agent must be running to update files")

    try:
        # Call agent's internal file update API with retry
        response = await agent_http_request(
            agent_name,
            "PUT",
            "/api/files",
            params={"path": path},
            json={"content": content},
            max_retries=3,
            retry_delay=1.0,
            timeout=60.0
        )
        if response.status_code == 200:
            result = response.json()
            return result
        else:
            raise HTTPException(
                status_code=response.status_code,
                detail=response.json().get("detail", f"Failed to update: {response.text}")
            )
    except httpx.ConnectError:
        # Agent server not ready - return 503 so tests can skip
        raise HTTPException(
            status_code=503,
            detail="Agent server not ready. The agent may still be starting up."
        )
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="File update timed out")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update file: {str(e)}")
