"""
Minimal conftest for unit tests that don't need backend fixtures.
"""

import pytest


def pytest_configure(config):
    """Configure custom markers."""
    config.addinivalue_line("markers", "unit: unit tests that don't need backend")
