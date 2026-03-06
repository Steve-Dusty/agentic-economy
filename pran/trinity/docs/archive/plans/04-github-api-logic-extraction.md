# Implementation Plan: GitHub API Logic Extraction

**Priority**: HIGH
**Report Section**: 2.2 - GitHub API Logic in Router
**Estimated Effort**: Medium
**Impact**: High - Moves ~300 lines of business logic from router to service layer

---

## Problem Statement

`routers/git.py` `initialize_github_sync` endpoint (lines 276-562) contains ~300 lines of GitHub API business logic that should be in `git_service.py`.

### Current Structure (Problematic)

```
routers/git.py (initialize_github_sync):
├── GitHub PAT validation
├── Repository existence check (GitHub API call)
├── Organization vs user detection (GitHub API call)
├── Repository creation (GitHub API call)
├── Container git directory detection
├── .gitignore creation
├── Git initialization commands (6 container exec calls)
├── Working branch creation (2 container exec calls)
├── Verification (container exec)
└── Database config creation
```

**Why this is a problem:**
1. Router should only handle HTTP request/response, not business logic
2. Cannot reuse GitHub repo creation logic elsewhere
3. Difficult to unit test (requires mocking FastAPI context)
4. Mixes infrastructure concerns (GitHub API) with routing
5. Makes the router file too long and hard to maintain

---

## Solution

Extract GitHub API logic and git initialization into `git_service.py`, leaving the router as a thin HTTP layer.

---

## Implementation Steps

### Step 1: Create GitHubService Class

**File**: `src/backend/services/github_service.py` (NEW)

```python
"""
GitHub API Service.

Handles all GitHub API interactions:
- Repository existence checking
- Organization detection
- Repository creation
- Token validation
"""
import httpx
import logging
from dataclasses import dataclass
from typing import Optional, Tuple
from enum import Enum

logger = logging.getLogger(__name__)


class OwnerType(Enum):
    """Type of GitHub repository owner."""
    USER = "user"
    ORGANIZATION = "org"


@dataclass
class GitHubRepoInfo:
    """Information about a GitHub repository."""
    exists: bool
    full_name: str
    owner: str
    name: str
    owner_type: Optional[OwnerType] = None
    private: Optional[bool] = None
    default_branch: Optional[str] = None


@dataclass
class GitHubCreateResult:
    """Result of creating a GitHub repository."""
    success: bool
    repo_url: Optional[str] = None
    error: Optional[str] = None


class GitHubError(Exception):
    """Base exception for GitHub API errors."""
    pass


class GitHubAuthError(GitHubError):
    """GitHub authentication failed."""
    pass


class GitHubPermissionError(GitHubError):
    """Insufficient permissions for operation."""
    pass


class GitHubService:
    """
    Service for GitHub API interactions.

    Centralizes all GitHub REST API calls.
    """

    API_BASE = "https://api.github.com"
    API_VERSION = "2022-11-28"

    def __init__(self, pat: str):
        """
        Initialize GitHub service with a Personal Access Token.

        Args:
            pat: GitHub Personal Access Token
        """
        self.pat = pat
        self._headers = {
            "Authorization": f"Bearer {pat}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": self.API_VERSION
        }

    async def _request(
        self,
        method: str,
        path: str,
        timeout: float = 10.0,
        **kwargs
    ) -> httpx.Response:
        """Make an authenticated request to GitHub API."""
        url = f"{self.API_BASE}{path}"
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.request(
                method, url,
                headers=self._headers,
                **kwargs
            )
            return response

    async def validate_token(self) -> Tuple[bool, Optional[str]]:
        """
        Validate the PAT and return the authenticated user.

        Returns:
            Tuple of (is_valid, username)
        """
        try:
            response = await self._request("GET", "/user")
            if response.status_code == 200:
                data = response.json()
                return True, data.get("login")
            elif response.status_code == 401:
                return False, None
            else:
                return False, None
        except Exception:
            return False, None

    async def get_owner_type(self, owner: str) -> Optional[OwnerType]:
        """
        Determine if an owner is a user or organization.

        Args:
            owner: GitHub username or organization name

        Returns:
            OwnerType or None if not found
        """
        try:
            response = await self._request("GET", f"/users/{owner}")
            if response.status_code == 200:
                data = response.json()
                if data.get("type") == "Organization":
                    return OwnerType.ORGANIZATION
                return OwnerType.USER
            return None
        except Exception:
            return None

    async def check_repo_exists(self, owner: str, name: str) -> GitHubRepoInfo:
        """
        Check if a repository exists.

        Args:
            owner: Repository owner (user or org)
            name: Repository name

        Returns:
            GitHubRepoInfo with existence and details
        """
        full_name = f"{owner}/{name}"
        try:
            response = await self._request("GET", f"/repos/{full_name}")
            if response.status_code == 200:
                data = response.json()
                return GitHubRepoInfo(
                    exists=True,
                    full_name=full_name,
                    owner=owner,
                    name=name,
                    private=data.get("private"),
                    default_branch=data.get("default_branch")
                )
            elif response.status_code == 404:
                return GitHubRepoInfo(
                    exists=False,
                    full_name=full_name,
                    owner=owner,
                    name=name
                )
            else:
                raise GitHubError(f"GitHub API error: {response.status_code}")
        except httpx.RequestError as e:
            raise GitHubError(f"Network error: {e}")

    async def create_repository(
        self,
        owner: str,
        name: str,
        private: bool = True,
        description: Optional[str] = None,
        auto_init: bool = False
    ) -> GitHubCreateResult:
        """
        Create a new GitHub repository.

        Args:
            owner: Repository owner (user or org)
            name: Repository name
            private: Whether repo should be private
            description: Optional repo description
            auto_init: Whether to initialize with README

        Returns:
            GitHubCreateResult with success status
        """
        # Determine owner type
        owner_type = await self.get_owner_type(owner)
        if owner_type is None:
            return GitHubCreateResult(
                success=False,
                error=f"Owner '{owner}' not found on GitHub"
            )

        # Build payload
        payload = {
            "name": name,
            "private": private,
            "auto_init": auto_init
        }
        if description:
            payload["description"] = description

        # Use correct endpoint
        if owner_type == OwnerType.ORGANIZATION:
            path = f"/orgs/{owner}/repos"
        else:
            path = "/user/repos"

        try:
            response = await self._request(
                "POST", path,
                json=payload,
                timeout=30.0
            )

            if response.status_code == 201:
                data = response.json()
                return GitHubCreateResult(
                    success=True,
                    repo_url=data.get("html_url")
                )
            else:
                error_data = response.json()
                error_msg = error_data.get("message", "Unknown error")

                # Add helpful context
                if owner_type == OwnerType.ORGANIZATION:
                    error_msg += (
                        f" (Organization: {owner}. Ensure PAT has "
                        "'repo' scope and admin access to this organization)"
                    )
                else:
                    error_msg += (
                        " (For personal repos, PAT needs "
                        "'repo' or 'public_repo' scope)"
                    )

                logger.error(
                    f"GitHub API Error: Status={response.status_code}, "
                    f"Response={error_data}, OwnerType={owner_type}"
                )

                return GitHubCreateResult(
                    success=False,
                    error=error_msg
                )

        except httpx.RequestError as e:
            return GitHubCreateResult(
                success=False,
                error=f"Network error: {e}"
            )
```

### Step 2: Add Git Initialization to git_service.py

**File**: `src/backend/services/git_service.py`

Add these functions:

```python
from dataclasses import dataclass
from typing import List, Optional
from services.docker_service import get_agent_container, execute_command_in_container
from services.github_service import GitHubService, GitHubError


@dataclass
class GitInitResult:
    """Result of git initialization in container."""
    success: bool
    git_dir: str
    working_branch: Optional[str] = None
    error: Optional[str] = None


async def initialize_git_in_container(
    agent_name: str,
    github_repo: str,
    github_pat: str,
    create_working_branch: bool = True
) -> GitInitResult:
    """
    Initialize git in an agent container.

    Performs:
    1. Detect git directory (workspace or home)
    2. Create .gitignore
    3. Initialize git repo
    4. Configure remote
    5. Create initial commit
    6. Push to GitHub
    7. Create working branch (optional)

    Args:
        agent_name: Name of the agent container
        github_repo: Full repo name (e.g., "owner/repo")
        github_pat: GitHub PAT for authentication
        create_working_branch: Whether to create a working branch

    Returns:
        GitInitResult with status and branch info
    """
    container_name = f"agent-{agent_name}"

    # Step 1: Determine git directory
    check_workspace = execute_command_in_container(
        container_name=container_name,
        command='bash -c "[ -d /home/developer/workspace ] && find /home/developer/workspace -mindepth 1 -maxdepth 1 | head -1 | wc -l"',
        timeout=5
    )

    workspace_has_content = (
        check_workspace.get("exit_code") == 0 and
        "1" in check_workspace.get("output", "")
    )

    git_dir = "/home/developer/workspace" if workspace_has_content else "/home/developer"

    # Step 2: Create .gitignore (if using home directory)
    if git_dir == "/home/developer":
        gitignore_content = """# Exclude sensitive and temporary files
.bash_logout
.bashrc
.profile
.bash_history
.cache/
.local/
.npm/
.ssh/
content/
"""
        execute_command_in_container(
            container_name=container_name,
            command=f'bash -c "cat > {git_dir}/.gitignore << \'EOF\'\n{gitignore_content}\nEOF\n"',
            timeout=5
        )

    # Step 3: Initialize git
    commands = [
        'git config --global user.email "trinity@agent.local"',
        'git config --global user.name "Trinity Agent"',
        'git config --global init.defaultBranch main',
        'git init',
        f'git remote add origin https://oauth2:{github_pat}@github.com/{github_repo}.git',
        'git add .',
        'git commit -m "Initial commit from Trinity Agent" || echo "Nothing to commit"',
        'git push -u origin main --force'
    ]

    for cmd in commands:
        result = execute_command_in_container(
            container_name=container_name,
            command=f'bash -c "cd {git_dir} && {cmd}"',
            timeout=60
        )
        if result.get("exit_code", 0) != 0:
            if "Nothing to commit" not in result.get("output", ""):
                return GitInitResult(
                    success=False,
                    git_dir=git_dir,
                    error=f"Git command failed: {cmd}\nOutput: {result.get('output', '')}"
                )

    # Step 4: Create working branch (optional)
    working_branch = None
    if create_working_branch:
        instance_id = generate_instance_id()
        working_branch = generate_working_branch(agent_name, instance_id)

        branch_commands = [
            f'git checkout -b {working_branch}',
            f'git push -u origin {working_branch}'
        ]

        for cmd in branch_commands:
            execute_command_in_container(
                container_name=container_name,
                command=f'bash -c "cd {git_dir} && {cmd}"',
                timeout=60
            )

    # Step 5: Verify
    verify_result = execute_command_in_container(
        container_name=container_name,
        command=f'bash -c "cd {git_dir} && git rev-parse --git-dir"',
        timeout=5
    )

    if verify_result.get("exit_code", 0) != 0:
        return GitInitResult(
            success=False,
            git_dir=git_dir,
            error="Git initialization verification failed"
        )

    return GitInitResult(
        success=True,
        git_dir=git_dir,
        working_branch=working_branch
    )
```

### Step 3: Simplify Router

**File**: `src/backend/routers/git.py`

Replace the 300-line endpoint with:

```python
from services.github_service import GitHubService, GitHubError
from services.git_service import initialize_git_in_container
from services.settings_service import get_github_pat  # From Plan 01


@router.post("/{agent_name}/git/initialize")
async def initialize_github_sync(
    agent_name: str,
    body: GitInitializeRequest,
    request: Request,
    current_user: User = Depends(get_current_user)
):
    """
    Initialize GitHub synchronization for an agent.
    """
    from services.docker_service import get_agent_container

    # Validate agent
    container = get_agent_container(agent_name)
    if not container:
        raise HTTPException(status_code=404, detail="Agent not found")
    if container.status != "running":
        raise HTTPException(status_code=400, detail="Agent must be running")

    # Check owner access
    if not db.can_user_share_agent(current_user.username, agent_name):
        raise HTTPException(status_code=403, detail="Only agent owners can initialize GitHub sync")

    # Check if already configured
    existing_config = git_service.get_agent_git_config(agent_name)
    if existing_config:
        raise HTTPException(
            status_code=409,
            detail=f"Git sync already configured. Repository: {existing_config.github_repo}"
        )

    # Get GitHub PAT
    github_pat = get_github_pat()
    if not github_pat:
        raise HTTPException(
            status_code=400,
            detail="GitHub PAT not configured. Please add it in Settings."
        )

    repo_full_name = f"{body.repo_owner}/{body.repo_name}"

    try:
        # Create repository if requested
        if body.create_repo:
            gh = GitHubService(github_pat)
            repo_info = await gh.check_repo_exists(body.repo_owner, body.repo_name)

            if not repo_info.exists:
                create_result = await gh.create_repository(
                    owner=body.repo_owner,
                    name=body.repo_name,
                    private=body.private,
                    description=body.description
                )
                if not create_result.success:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Failed to create repository: {create_result.error}"
                    )

        # Initialize git in container
        init_result = await initialize_git_in_container(
            agent_name=agent_name,
            github_repo=repo_full_name,
            github_pat=github_pat
        )

        if not init_result.success:
            raise HTTPException(
                status_code=500,
                detail=f"Git initialization failed: {init_result.error}"
            )

        # Store configuration
        config = await git_service.create_git_config_for_agent(
            agent_name=agent_name,
            github_repo=repo_full_name,
            instance_id=git_service.generate_instance_id()
        )

        return {
            "success": True,
            "message": "GitHub sync initialized successfully",
            "github_repo": repo_full_name,
            "working_branch": init_result.working_branch,
            "repo_url": f"https://github.com/{repo_full_name}"
        }

    except HTTPException:
        raise
    except GitHubError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Initialization failed: {e}")
```

---

## Files Changed

| File | Change |
|------|--------|
| `services/github_service.py` | **NEW** - GitHub API client |
| `services/git_service.py` | Add `initialize_git_in_container()` |
| `routers/git.py` | Reduce from ~300 lines to ~60 lines |

---

## Testing

1. **Unit Tests**: `tests/test_github_service.py`
   ```python
   @pytest.mark.asyncio
   async def test_check_repo_exists_found():
       # Mock httpx response
       service = GitHubService("test-pat")
       # Assert returns GitHubRepoInfo with exists=True

   @pytest.mark.asyncio
   async def test_create_repository_org():
       # Mock httpx, test org endpoint used
       pass

   @pytest.mark.asyncio
   async def test_create_repository_user():
       # Mock httpx, test user endpoint used
       pass
   ```

2. **Integration Tests**: `tests/test_git_endpoints.py`
   - Test initialize endpoint with mocked GitHub service
   - Test error cases (no PAT, repo exists, permission denied)

3. **Manual Testing**:
   - Initialize new repo for existing agent
   - Initialize with org owner
   - Initialize with user owner
   - Test with invalid PAT

---

## Benefits

1. **Separation of Concerns**: Router handles HTTP, service handles logic
2. **Reusability**: `GitHubService` can be used elsewhere
3. **Testability**: Can unit test GitHub logic without FastAPI
4. **Maintainability**: ~300 lines → ~60 lines in router
5. **Error Handling**: Structured exceptions instead of inline checks
6. **Type Safety**: Dataclasses for responses
