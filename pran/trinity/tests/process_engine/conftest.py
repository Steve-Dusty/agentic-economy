"""
Process Engine Test Configuration

Sets up imports for process_engine module without triggering
the main services/__init__.py which has many dependencies.
"""

import sys
from pathlib import Path
import pytest

# Add src/backend to path for direct imports
_project_root = Path(__file__).resolve().parent.parent.parent
_backend_path = str(_project_root / 'src' / 'backend')
if _backend_path not in sys.path:
    sys.path.insert(0, _backend_path)

# Add src to path (for compatibility with main conftest)
_src_path = str(_project_root / 'src')
if _src_path not in sys.path:
    sys.path.insert(0, _src_path)


# Override session fixtures from root conftest to avoid API connections
# These are no-ops for our unit tests
@pytest.fixture(scope="session")
def api_config():
    """Stub fixture - process engine unit tests don't need API."""
    return None


@pytest.fixture(scope="session")
def api_client():
    """Stub fixture - process engine unit tests don't need API."""
    yield None


@pytest.fixture(scope="session")
def unauthenticated_client():
    """Stub fixture - process engine unit tests don't need API."""
    yield None
