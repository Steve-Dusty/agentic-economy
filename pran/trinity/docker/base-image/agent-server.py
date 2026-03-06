#!/usr/bin/env python3
"""
Agent Server - Entry Point

This is a thin wrapper that imports and runs the agent server from the
agent_server package. All actual implementation is in the agent_server/ directory.

SECURITY: This server is NOT exposed externally. All access goes through
the authenticated Trinity backend at /api/agents/{name}/chat
"""

from agent_server import run_server

if __name__ == "__main__":
    run_server()
