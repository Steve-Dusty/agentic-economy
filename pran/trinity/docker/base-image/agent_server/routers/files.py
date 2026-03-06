"""
File browser endpoints.
"""
import logging
import mimetypes
import shutil
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import PlainTextResponse, FileResponse
from pydantic import BaseModel


class FileUpdateRequest(BaseModel):
    """Request body for file updates."""
    content: str

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/api/files")
async def list_files(path: str = "/home/developer", show_hidden: bool = False):
    """
    List files in the workspace directory recursively.
    Only allows access to /home/developer for security.

    Args:
        path: Directory path to list
        show_hidden: If True, include hidden files (starting with .)

    Returns a hierarchical tree structure with folders and files.
    """
    # Security: Only allow workspace access
    allowed_base = Path("/home/developer")
    requested_path = Path(path).resolve()

    # Ensure requested path is within workspace
    if not str(requested_path).startswith(str(allowed_base)):
        raise HTTPException(status_code=403, detail="Access denied: only /home/developer accessible")

    if not requested_path.exists():
        raise HTTPException(status_code=404, detail=f"Path not found: {path}")

    def build_tree(directory: Path, base_path: Path, include_hidden: bool) -> dict:
        """Build a hierarchical tree structure from a directory."""
        items = []
        total_files = 0

        try:
            # Get all items in directory
            dir_items = sorted(directory.iterdir(), key=lambda x: (not x.is_dir(), x.name.lower()))

            for item in dir_items:
                # Skip hidden items unless show_hidden is True
                if item.name.startswith('.') and not include_hidden:
                    continue

                try:
                    stat = item.stat()
                    relative_path = item.relative_to(base_path)

                    if item.is_dir():
                        # Recursively build tree for subdirectory
                        subtree = build_tree(item, base_path, include_hidden)
                        items.append({
                            "name": item.name,
                            "path": str(relative_path),
                            "type": "directory",
                            "children": subtree["children"],
                            "file_count": subtree["file_count"],
                            "modified": datetime.fromtimestamp(stat.st_mtime).isoformat()
                        })
                        total_files += subtree["file_count"]
                    else:
                        # It's a file
                        items.append({
                            "name": item.name,
                            "path": str(relative_path),
                            "type": "file",
                            "size": stat.st_size,
                            "modified": datetime.fromtimestamp(stat.st_mtime).isoformat()
                        })
                        total_files += 1

                except Exception as e:
                    logger.warning(f"Failed to process item {item}: {e}")
                    continue

        except Exception as e:
            logger.error(f"Failed to read directory {directory}: {e}")

        return {"children": items, "file_count": total_files}

    try:
        tree_data = build_tree(requested_path, allowed_base, show_hidden)

        return {
            "base_path": str(allowed_base),
            "requested_path": str(requested_path.relative_to(allowed_base)) if requested_path != allowed_base else ".",
            "tree": tree_data["children"],
            "total_files": tree_data["file_count"],
            "show_hidden": show_hidden
        }

    except Exception as e:
        logger.error(f"File listing error: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to list files: {str(e)}")


@router.get("/api/files/download")
async def download_file(path: str):
    """
    Download a file from the workspace.
    Only allows access to /home/developer for security.
    Max file size: 100MB

    Returns file content as plain text.
    """
    # Security: Only allow workspace access
    allowed_base = Path("/home/developer")

    # Handle both absolute and relative paths
    if path.startswith('/'):
        requested_path = Path(path).resolve()
    else:
        requested_path = (allowed_base / path).resolve()

    # Ensure requested path is within workspace
    if not str(requested_path).startswith(str(allowed_base)):
        raise HTTPException(status_code=403, detail="Access denied: only /home/developer accessible")

    if not requested_path.exists():
        raise HTTPException(status_code=404, detail=f"File not found: {path}")

    if not requested_path.is_file():
        raise HTTPException(status_code=400, detail=f"Not a file: {path}")

    # Check file size (100MB limit)
    max_size = 100 * 1024 * 1024  # 100MB
    file_size = requested_path.stat().st_size
    if file_size > max_size:
        raise HTTPException(status_code=413, detail=f"File too large: {file_size} bytes (max {max_size})")

    try:
        # Read file content
        content = requested_path.read_text(encoding='utf-8', errors='replace')
        return PlainTextResponse(content=content)

    except Exception as e:
        logger.error(f"File download error: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to read file: {str(e)}")


# Protected paths that cannot be deleted
PROTECTED_PATHS = [
    "CLAUDE.md",
    ".trinity",
    ".git",
    ".gitignore",
    ".env",
    ".mcp.json",
    ".mcp.json.template",
]

# Paths that cannot be edited (subset of PROTECTED_PATHS)
# CLAUDE.md and .mcp.json ARE editable since users need to modify them
EDIT_PROTECTED_PATHS = [
    ".trinity",
    ".git",
    ".gitignore",
    ".env",
    ".mcp.json.template",
]


def _is_protected_path(path: Path) -> bool:
    """Check if path is a protected file/directory (for deletion)."""
    for protected in PROTECTED_PATHS:
        if path.name == protected:
            return True
        # Check parent directories too
        for parent in path.parents:
            if parent.name == protected:
                return True
    return False


def _is_edit_protected_path(path: Path) -> bool:
    """Check if path is protected from editing."""
    for protected in EDIT_PROTECTED_PATHS:
        if path.name == protected:
            return True
        # Check parent directories too
        for parent in path.parents:
            if parent.name == protected:
                return True
    return False


@router.delete("/api/files")
async def delete_file(path: str):
    """
    Delete a file or directory from the workspace.
    Only allows access to /home/developer for security.
    Cannot delete protected paths (CLAUDE.md, .trinity, .git, etc.)
    """
    # Security: Only allow workspace access
    allowed_base = Path("/home/developer")

    # Handle both absolute and relative paths
    if path.startswith('/'):
        requested_path = Path(path).resolve()
    else:
        requested_path = (allowed_base / path).resolve()

    # Ensure requested path is within workspace
    if not str(requested_path).startswith(str(allowed_base)):
        raise HTTPException(status_code=403, detail="Access denied: only /home/developer accessible")

    # Prevent deleting the base directory itself
    if requested_path == allowed_base:
        raise HTTPException(status_code=403, detail="Cannot delete home directory")

    # Check if it's a protected path
    if _is_protected_path(requested_path):
        raise HTTPException(
            status_code=403,
            detail=f"Cannot delete protected path: {requested_path.name}"
        )

    if not requested_path.exists():
        raise HTTPException(status_code=404, detail=f"File not found: {path}")

    try:
        file_type = "directory" if requested_path.is_dir() else "file"
        file_count = 0

        if requested_path.is_dir():
            # Count files before deletion
            for _ in requested_path.rglob("*"):
                file_count += 1
            shutil.rmtree(requested_path)
        else:
            file_count = 1
            requested_path.unlink()

        logger.info(f"Deleted {file_type}: {requested_path}")
        return {
            "success": True,
            "deleted": path,
            "type": file_type,
            "file_count": file_count
        }

    except Exception as e:
        logger.error(f"File delete error: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to delete: {str(e)}")


@router.get("/api/files/preview")
async def preview_file(path: str):
    """
    Get file with proper MIME type for preview.
    Supports images, videos, audio, PDFs, and text files.
    Only allows access to /home/developer for security.
    Max file size: 100MB
    """
    # Security: Only allow workspace access
    allowed_base = Path("/home/developer")

    # Handle both absolute and relative paths
    if path.startswith('/'):
        requested_path = Path(path).resolve()
    else:
        requested_path = (allowed_base / path).resolve()

    # Ensure requested path is within workspace
    if not str(requested_path).startswith(str(allowed_base)):
        raise HTTPException(status_code=403, detail="Access denied: only /home/developer accessible")

    if not requested_path.exists():
        raise HTTPException(status_code=404, detail=f"File not found: {path}")

    if not requested_path.is_file():
        raise HTTPException(status_code=400, detail=f"Not a file: {path}")

    # Check file size (100MB limit)
    max_size = 100 * 1024 * 1024  # 100MB
    file_size = requested_path.stat().st_size
    if file_size > max_size:
        raise HTTPException(status_code=413, detail=f"File too large: {file_size} bytes (max {max_size})")

    try:
        # Detect MIME type
        mime_type, _ = mimetypes.guess_type(str(requested_path))
        if mime_type is None:
            # Default to binary for unknown types
            mime_type = "application/octet-stream"

        # Return file with correct Content-Type for browser preview
        return FileResponse(
            path=requested_path,
            media_type=mime_type,
            filename=requested_path.name
        )

    except Exception as e:
        logger.error(f"File preview error: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to preview file: {str(e)}")


@router.put("/api/files")
async def update_file(path: str, request: FileUpdateRequest, platform: bool = False):
    """
    Update or create a file's content in the workspace.
    Only allows access to /home/developer for security.
    Cannot modify protected paths (.trinity, .git, etc.) unless platform=true.
    Creates parent directories if they don't exist.

    Args:
        path: File path to update/create (query parameter)
        request: Request body with content
        platform: If true, allows writes to .trinity directory (platform-initiated)

    Returns:
        Success status and file info
    """
    # Security: Only allow workspace access
    allowed_base = Path("/home/developer")

    # Handle both absolute and relative paths
    if path.startswith('/'):
        requested_path = Path(path).resolve()
    else:
        requested_path = (allowed_base / path).resolve()

    # Ensure requested path is within workspace
    if not str(requested_path).startswith(str(allowed_base)):
        raise HTTPException(status_code=403, detail="Access denied: only /home/developer accessible")

    # Check if it's a protected path (for editing)
    # Platform writes can bypass .trinity protection (but not .git, .env, etc.)
    if _is_edit_protected_path(requested_path):
        # Allow platform writes to .trinity directory only
        is_trinity_path = any(p.name == ".trinity" for p in [requested_path] + list(requested_path.parents))
        if not (platform and is_trinity_path):
            raise HTTPException(
                status_code=403,
                detail=f"Cannot edit protected path: {requested_path.name}"
            )

    # If path exists and is a directory, reject
    if requested_path.exists() and not requested_path.is_file():
        raise HTTPException(status_code=400, detail=f"Not a file: {path}")

    try:
        # Create parent directories if they don't exist
        requested_path.parent.mkdir(parents=True, exist_ok=True)

        # Write the new content
        requested_path.write_text(request.content, encoding='utf-8')
        stat = requested_path.stat()

        logger.info(f"Updated file: {requested_path}")
        return {
            "success": True,
            "path": path,
            "size": stat.st_size,
            "modified": datetime.fromtimestamp(stat.st_mtime).isoformat()
        }

    except Exception as e:
        logger.error(f"File update error: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to update file: {str(e)}")
