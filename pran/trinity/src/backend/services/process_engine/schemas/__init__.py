"""
Process Engine Schemas

JSON Schema definitions for process definitions.
"""

from pathlib import Path

SCHEMA_DIR = Path(__file__).parent


def get_process_definition_schema_path() -> Path:
    """Get path to process definition JSON schema."""
    return SCHEMA_DIR / "process-definition.schema.json"
