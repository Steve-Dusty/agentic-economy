"""
Agent Service Deploy - Local agent deployment logic.

Contains the business logic for deploying local agents via MCP.
"""
import base64
import tarfile
import tempfile
import shutil
import asyncio
import logging
from pathlib import Path
from io import BytesIO

from fastapi import HTTPException, Request

from models import (
    AgentConfig,
    AgentStatus,
    User,
    DeployLocalRequest,
    DeployLocalResponse,
    VersioningInfo,
    CredentialImportResult,
)
from services.template_service import is_trinity_compatible
from services.docker_service import get_agent_container
from services.docker_utils import container_stop
from utils.helpers import sanitize_agent_name
from .helpers import get_agents_by_prefix, get_next_version_name, get_latest_version

logger = logging.getLogger(__name__)

# Size limits for local deployment
MAX_ARCHIVE_SIZE = 50 * 1024 * 1024  # 50 MB
MAX_CREDENTIALS = 100
MAX_FILES = 1000


# =============================================================================
# Safe Tar Extraction Utilities
# =============================================================================

def _is_path_within(base: Path, target: Path) -> bool:
    """
    Check if target path is within base directory.
    
    Uses Path.resolve() to handle symlinks and normalize paths.
    Returns True if target is inside base (or is base itself).
    """
    try:
        # resolve() normalizes the path and resolves symlinks
        # We use strict=False because target may not exist yet during extraction
        base_resolved = base.resolve()
        target_resolved = target.resolve()
        
        # Check if target starts with base path
        return str(target_resolved).startswith(str(base_resolved) + "/") or \
               target_resolved == base_resolved
    except (OSError, ValueError):
        return False


def _validate_tar_member(member: tarfile.TarInfo, base_dir: Path) -> tuple[bool, str]:
    """
    Validate a tar archive member for safe extraction.
    
    Checks:
    - Destination path stays within base_dir
    - No absolute paths
    - Symlinks/hardlinks only point within base_dir
    - No special file types (devices, FIFOs)
    
    Args:
        member: The tar archive member to validate
        base_dir: The base directory for extraction
        
    Returns:
        Tuple of (is_valid, error_message). If valid, error_message is empty.
    """
    member_name = member.name
    
    # Reject absolute paths
    if member_name.startswith('/'):
        return False, f"Absolute path not allowed: {member_name}"
    
    # Reject path traversal in member name
    if '..' in member_name.split('/'):
        return False, f"Path traversal not allowed: {member_name}"
    
    # Calculate the destination path
    dest_path = base_dir / member_name
    
    # Verify destination stays within base_dir
    if not _is_path_within(base_dir, dest_path):
        return False, f"Path escapes extraction directory: {member_name}"
    
    # Reject special file types (devices, FIFOs)
    if member.ischr() or member.isblk():
        return False, f"Device files not allowed: {member_name}"
    if member.isfifo():
        return False, f"FIFO files not allowed: {member_name}"
    
    # Validate symlinks
    if member.issym():
        linkname = member.linkname
        
        # Reject absolute symlink targets
        if linkname.startswith('/'):
            return False, f"Absolute symlink target not allowed: {member_name} -> {linkname}"
        
        # Calculate where the symlink would point
        # Symlink is relative to the directory containing it
        link_dir = dest_path.parent
        link_target = (link_dir / linkname).resolve()
        
        # Verify symlink target stays within base_dir
        if not _is_path_within(base_dir, link_target):
            return False, f"Symlink escapes extraction directory: {member_name} -> {linkname}"
    
    # Validate hardlinks
    if member.islnk():
        linkname = member.linkname
        
        # Reject absolute hardlink targets
        if linkname.startswith('/'):
            return False, f"Absolute hardlink target not allowed: {member_name} -> {linkname}"
        
        # Hardlink target is relative to archive root (base_dir)
        link_target = base_dir / linkname
        
        # Verify hardlink target stays within base_dir
        if not _is_path_within(base_dir, link_target):
            return False, f"Hardlink escapes extraction directory: {member_name} -> {linkname}"
    
    return True, ""


def _safe_extract_tar(tar: tarfile.TarFile, dest_dir: Path, max_files: int) -> None:
    """
    Safely extract a tar archive with full validation.
    
    Validates all members before extraction and raises HTTPException
    if any member fails validation.
    
    Args:
        tar: Open tarfile object
        dest_dir: Destination directory for extraction
        max_files: Maximum number of files allowed
        
    Raises:
        HTTPException: If archive validation fails
    """
    members = tar.getmembers()
    
    # Check file count
    if len(members) > max_files:
        raise HTTPException(
            status_code=400,
            detail={
                "error": f"Archive exceeds maximum file count of {max_files}",
                "code": "TOO_MANY_FILES"
            }
        )
    
    # Validate all members before extraction
    safe_members = []
    for member in members:
        is_valid, error_msg = _validate_tar_member(member, dest_dir)
        if not is_valid:
            raise HTTPException(
                status_code=400,
                detail={
                    "error": f"Invalid archive: {error_msg}",
                    "code": "INVALID_ARCHIVE"
                }
            )
        safe_members.append(member)
    
    # Extract validated members
    tar.extractall(dest_dir, members=safe_members)


async def deploy_local_agent_logic(
    body: DeployLocalRequest,
    current_user: User,
    request: Request,
    create_agent_fn
) -> DeployLocalResponse:
    """
    Deploy a Trinity-compatible local agent.

    This receives a base64-encoded tar.gz archive of a local agent
    directory, validates it's Trinity-compatible (has template.yaml), handles
    versioning if an agent with the same name exists, and creates the agent.

    CRED-002: Credentials are now injected after agent creation via
    inject_credentials endpoint, not during deployment.

    Args:
        body: Deploy request with archive and credentials
        current_user: Authenticated user
        request: FastAPI request object
        create_agent_fn: Function to create agent (create_agent_internal)

    Returns:
        DeployLocalResponse with deployment details
    """
    import httpx

    temp_dir = None

    try:
        # 1. Validate archive size
        try:
            archive_bytes = base64.b64decode(body.archive)
        except Exception as e:
            raise HTTPException(
                status_code=400,
                detail={
                    "error": f"Invalid base64 encoding: {e}",
                    "code": "INVALID_ARCHIVE"
                }
            )

        if len(archive_bytes) > MAX_ARCHIVE_SIZE:
            raise HTTPException(
                status_code=400,
                detail={
                    "error": f"Archive exceeds maximum size of {MAX_ARCHIVE_SIZE // (1024*1024)}MB",
                    "code": "ARCHIVE_TOO_LARGE"
                }
            )

        # 2. Validate credentials count
        if body.credentials and len(body.credentials) > MAX_CREDENTIALS:
            raise HTTPException(
                status_code=400,
                detail={
                    "error": f"Credentials exceed maximum count of {MAX_CREDENTIALS}",
                    "code": "TOO_MANY_CREDENTIALS"
                }
            )

        # 3. Extract archive to temp directory
        temp_dir = Path(tempfile.mkdtemp(prefix="trinity-deploy-"))
        try:
            with tarfile.open(fileobj=BytesIO(archive_bytes), mode='r:gz') as tar:
                # Security: Safe extraction with full validation
                # - Validates paths stay within temp_dir
                # - Blocks symlinks/hardlinks pointing outside
                # - Rejects device files and FIFOs
                _safe_extract_tar(tar, temp_dir, MAX_FILES)
        except tarfile.TarError as e:
            raise HTTPException(
                status_code=400,
                detail={
                    "error": f"Invalid tar.gz archive: {e}",
                    "code": "INVALID_ARCHIVE"
                }
            )

        # 4. Find the root directory (handle nested extraction)
        contents = list(temp_dir.iterdir())
        if len(contents) == 1 and contents[0].is_dir():
            extract_root = contents[0]
        else:
            extract_root = temp_dir

        # 5. Validate Trinity-compatible
        is_compatible, error_msg, template_data = is_trinity_compatible(extract_root)
        if not is_compatible:
            raise HTTPException(
                status_code=400,
                detail={
                    "error": f"Agent is not Trinity-compatible: {error_msg}",
                    "code": "NOT_TRINITY_COMPATIBLE"
                }
            )

        # 6. Determine agent name
        base_name = body.name or template_data.get("name")
        if not base_name:
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "No agent name specified and template.yaml has no name field",
                    "code": "MISSING_NAME"
                }
            )

        base_name = sanitize_agent_name(base_name)

        # 7. Version handling
        version_name = get_next_version_name(base_name)
        previous_version = get_latest_version(base_name)
        previous_stopped = False

        if previous_version and previous_version.status == "running":
            # Stop the previous version
            try:
                container = get_agent_container(previous_version.name)
                if container:
                    await container_stop(container)
                    previous_stopped = True
                    logger.info(f"Stopped previous version: {previous_version.name}")
            except Exception as e:
                logger.warning(f"Failed to stop previous version {previous_version.name}: {e}")

        # 8. CRED-002: Credentials are passed to agent after creation via inject
        # Just track what credentials were provided
        cred_results = {}
        if body.credentials:
            for key, value in body.credentials.items():
                cred_results[key] = CredentialImportResult(
                    status="pending_injection",
                    name=key,
                    original=None
                )

        # 9. Copy to templates directory
        # Try /agent-configs/templates first, but check if writable (not just if exists)
        # The read-only mount makes this path exist but not writable
        templates_dir = Path("/agent-configs/templates")

        # Check if writable by attempting to create a test file
        try:
            test_file = templates_dir / ".write_test"
            test_file.touch()
            test_file.unlink()
        except (OSError, PermissionError):
            # Fall back to local config path
            templates_dir = Path("./config/agent-templates")

        if not templates_dir.exists():
            templates_dir.mkdir(parents=True, exist_ok=True)

        dest_path = templates_dir / version_name
        if dest_path.exists():
            shutil.rmtree(dest_path)

        shutil.copytree(extract_root, dest_path)
        logger.info(f"Copied agent template to: {dest_path}")

        # 10. Create agent
        # Extract runtime config from template
        runtime_config = template_data.get("runtime", {})
        runtime_type = None
        runtime_model = None
        if isinstance(runtime_config, dict):
            runtime_type = runtime_config.get("type")
            runtime_model = runtime_config.get("model")
        elif isinstance(runtime_config, str):
            runtime_type = runtime_config

        agent_config = AgentConfig(
            name=version_name,
            template=f"local:{version_name}",
            type=template_data.get("type", "business-assistant"),
            resources=template_data.get("resources", {"cpu": "2", "memory": "4g"}),
            runtime=runtime_type,
            runtime_model=runtime_model
        )

        agent_status = await create_agent_fn(
            agent_config,
            current_user,
            request,
            skip_name_sanitization=True
        )

        # 11. CRED-002: Inject credentials using new simplified system
        if body.credentials:
            try:
                # Wait a moment for the agent to start
                await asyncio.sleep(2)

                # Build .env content from credentials
                env_content = "\n".join(f"{k}={v}" for k, v in body.credentials.items())

                async with httpx.AsyncClient(timeout=30.0) as client:
                    await client.post(
                        f"http://agent-{version_name}:8000/api/credentials/inject",
                        json={"files": {".env": env_content}}
                    )
                    logger.info(f"Injected {len(body.credentials)} credentials into {version_name}")

                # Update credential results to show success
                for key in cred_results:
                    cred_results[key] = CredentialImportResult(
                        status="injected",
                        name=key,
                        original=None
                    )
            except Exception as e:
                logger.warning(f"Failed to inject credentials: {e}")

        # 12. Inject CLAUDE.md custom instructions if present
        claude_md_path = extract_root / "CLAUDE.md"
        if claude_md_path.exists():
            try:
                # Wait for agent to be ready if we didn't already wait for credentials
                if not body.credentials:
                    await asyncio.sleep(2)

                custom_prompt = claude_md_path.read_text()
                async with httpx.AsyncClient(timeout=30.0) as client:
                    await client.post(
                        f"http://agent-{version_name}:8000/api/trinity/inject",
                        json={"custom_prompt": custom_prompt}
                    )
                    logger.info(f"Injected CLAUDE.md ({len(custom_prompt)} chars) into {version_name}")
            except Exception as e:
                logger.warning(f"Failed to inject CLAUDE.md: {e}")

        # 13. Return response
        return DeployLocalResponse(
            status="success",
            agent=agent_status,
            versioning=VersioningInfo(
                base_name=base_name,
                previous_version=previous_version.name if previous_version else None,
                previous_version_stopped=previous_stopped,
                new_version=version_name
            ),
            credentials_imported={k: v.dict() for k, v in cred_results.items()},
            credentials_injected=len(cred_results)
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to deploy local agent: {str(e)}"
        )
    finally:
        # Cleanup temp directory
        if temp_dir and temp_dir.exists():
            try:
                shutil.rmtree(temp_dir)
            except Exception:
                pass
