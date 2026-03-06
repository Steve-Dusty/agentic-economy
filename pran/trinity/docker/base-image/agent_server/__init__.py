"""
Agent Server Package

Internal API for Claude Code agents running inside Trinity agent containers.
This server runs on port 8000 and is NOT exposed externally - all access
goes through the authenticated Trinity backend.
"""
from .main import app, run_server
from .state import agent_state

__all__ = ["app", "run_server", "agent_state"]
__version__ = "2.0.0"
