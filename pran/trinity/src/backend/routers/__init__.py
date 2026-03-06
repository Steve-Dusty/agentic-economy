"""
Trinity API routers.
"""
from .auth import router as auth_router
from .agents import router as agents_router
from .credentials import router as credentials_router
from .templates import router as templates_router
from .sharing import router as sharing_router
from .mcp_keys import router as mcp_keys_router
from .chat import router as chat_router

__all__ = [
    "auth_router",
    "agents_router",
    "credentials_router",
    "templates_router",
    "sharing_router",
    "mcp_keys_router",
    "chat_router",
]
