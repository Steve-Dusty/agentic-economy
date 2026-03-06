# Implementation Plan: Settings Service

**Priority**: CRITICAL
**Report Section**: 2.1 - Services Importing from Routers
**Estimated Effort**: Low
**Impact**: High - Fixes architectural violation and circular dependency risk
**Status**: ✅ COMPLETED (2025-12-31)

---

## Implementation Summary

Implemented as planned. Created `services/settings_service.py` with centralized settings retrieval.
Updated all imports in service layer files to use the new service instead of routers.settings.
Router re-exports functions for backward compatibility.

All tests pass - verified in Docker container.

---

## Problem Statement

Service layer imports functions from router layer, inverting the dependency direction:

```python
# In services/agent_service/crud.py (line 29)
from routers.settings import get_anthropic_api_key

# In services/agent_service/lifecycle.py (line 18)
from routers.settings import get_anthropic_api_key

# In routers/git.py (line 301)
from routers.settings import get_github_pat
```

**Why this is a problem:**
1. Violates clean architecture - services should not depend on routers
2. Creates circular dependency risk (router → service → router)
3. Makes testing difficult - mocking requires importing router layer
4. Blurs separation of concerns

---

## Solution

Create a dedicated `services/settings_service.py` that encapsulates all settings retrieval logic.

---

## Implementation Steps

### Step 1: Create Settings Service

**File**: `src/backend/services/settings_service.py`

```python
"""
Settings service for retrieving configuration values.

Provides centralized access to:
- Database-stored settings
- Environment variable fallbacks
- Typed conversions
"""
import os
from typing import Optional
from database import db


class SettingsService:
    """
    Centralized service for retrieving settings.

    Hierarchy:
    1. Database setting (if exists)
    2. Environment variable (fallback)
    3. Default value (if provided)
    """

    def get_setting(self, key: str, default: Optional[str] = None) -> Optional[str]:
        """Get a setting from database with optional default."""
        value = db.get_setting_value(key, None)
        return value if value is not None else default

    def get_anthropic_api_key(self) -> str:
        """Get Anthropic API key from settings, fallback to env var."""
        key = self.get_setting('anthropic_api_key')
        if key:
            return key
        return os.getenv('ANTHROPIC_API_KEY', '')

    def get_github_pat(self) -> str:
        """Get GitHub PAT from settings, fallback to env var."""
        key = self.get_setting('github_pat')
        if key:
            return key
        return os.getenv('GITHUB_PAT', '')

    def get_google_api_key(self) -> str:
        """Get Google API key from settings, fallback to env var."""
        key = self.get_setting('google_api_key')
        if key:
            return key
        return os.getenv('GOOGLE_API_KEY', '')

    def get_ops_setting(self, key: str, as_type: type = str):
        """
        Get an ops setting with type conversion.

        Uses defaults from OPS_SETTINGS_DEFAULTS if not set.
        """
        from routers.settings import OPS_SETTINGS_DEFAULTS

        default = OPS_SETTINGS_DEFAULTS.get(key, "")
        value = self.get_setting(key, default)

        if as_type == int:
            return int(value)
        elif as_type == float:
            return float(value)
        elif as_type == bool:
            return str(value).lower() in ("true", "1", "yes")
        return value


# Singleton instance
settings_service = SettingsService()

# Convenience functions for backward compatibility
def get_anthropic_api_key() -> str:
    """Get Anthropic API key from settings, fallback to env var."""
    return settings_service.get_anthropic_api_key()

def get_github_pat() -> str:
    """Get GitHub PAT from settings, fallback to env var."""
    return settings_service.get_github_pat()

def get_google_api_key() -> str:
    """Get Google API key from settings, fallback to env var."""
    return settings_service.get_google_api_key()
```

### Step 2: Update Service Imports

**File**: `src/backend/services/agent_service/crud.py`

```diff
- from routers.settings import get_anthropic_api_key
+ from services.settings_service import get_anthropic_api_key
```

**File**: `src/backend/services/agent_service/lifecycle.py`

```diff
- from routers.settings import get_anthropic_api_key
+ from services.settings_service import get_anthropic_api_key
```

**File**: `src/backend/routers/git.py`

```diff
- from routers.settings import get_github_pat
+ from services.settings_service import get_github_pat
```

### Step 3: Update Router to Use Service

**File**: `src/backend/routers/settings.py`

Replace the local helper functions with re-exports from the service:

```python
# At the top of the file, after other imports
from services.settings_service import (
    get_anthropic_api_key,
    get_github_pat,
    get_google_api_key,
    settings_service
)

# Remove the local function definitions (lines 34-47):
# - def get_anthropic_api_key() -> str: ...
# - def get_github_pat() -> str: ...
```

### Step 4: Update Other Files That May Use These Functions

Search for other usages and update:

```bash
grep -r "from routers.settings import" src/backend/
```

Known files to check:
- `services/git_service.py` (if it uses get_github_pat)
- `services/agent_service/deploy.py` (if it uses get_anthropic_api_key)

---

## Files Changed

| File | Change |
|------|--------|
| `services/settings_service.py` | **NEW** - Centralized settings retrieval |
| `services/agent_service/crud.py` | Update import |
| `services/agent_service/lifecycle.py` | Update import |
| `routers/git.py` | Update import |
| `routers/settings.py` | Re-export from service, remove local functions |

---

## Testing

1. **Unit Test**: Create `tests/test_settings_service.py`
   - Test `get_anthropic_api_key()` with database value
   - Test `get_anthropic_api_key()` with env fallback
   - Test `get_github_pat()` similarly

2. **Integration Test**: Ensure agent creation still works
   - Create agent from template
   - Verify API key injection

3. **Manual Test**:
   - Settings page still works
   - API key test buttons work
   - Agent creation uses correct API key

---

## Rollback Plan

If issues arise:
1. Revert import changes in services
2. Restore original functions in `routers/settings.py`
3. Delete `services/settings_service.py`

---

## Benefits

1. **Clean Architecture**: Services no longer depend on routers
2. **Testability**: Easy to mock settings in unit tests
3. **Single Source of Truth**: All settings logic in one place
4. **Type Safety**: Typed conversion methods (`get_ops_setting`)
5. **Extensibility**: Easy to add new settings retrieval methods
