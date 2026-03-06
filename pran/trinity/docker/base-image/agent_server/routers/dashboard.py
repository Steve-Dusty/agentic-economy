"""
Agent Dashboard endpoint.

Reads and serves dashboard configuration from dashboard.yaml file.
"""
import logging
from pathlib import Path
from typing import Optional, Dict, Any, List
from datetime import datetime

from fastapi import APIRouter
import yaml

logger = logging.getLogger(__name__)
router = APIRouter()


def get_dashboard_path() -> Path:
    """Get the fixed path to dashboard.yaml."""
    return Path("/home/developer/dashboard.yaml")


def validate_widget(widget: Dict[str, Any], index: int) -> Optional[str]:
    """Validate a single widget. Returns error message if invalid."""
    valid_types = [
        'metric', 'status', 'progress', 'text', 'markdown',
        'table', 'list', 'link', 'image', 'divider', 'spacer'
    ]

    widget_type = widget.get('type')
    if not widget_type:
        return f"Widget {index}: missing 'type' field"

    if widget_type not in valid_types:
        return f"Widget {index}: invalid type '{widget_type}'. Valid types: {', '.join(valid_types)}"

    # Type-specific validation
    if widget_type == 'metric':
        if 'label' not in widget:
            return f"Widget {index} (metric): missing required 'label' field"
        if 'value' not in widget:
            return f"Widget {index} (metric): missing required 'value' field"

    elif widget_type == 'status':
        if 'label' not in widget:
            return f"Widget {index} (status): missing required 'label' field"
        if 'value' not in widget:
            return f"Widget {index} (status): missing required 'value' field"
        if 'color' not in widget:
            return f"Widget {index} (status): missing required 'color' field"

    elif widget_type == 'progress':
        if 'label' not in widget:
            return f"Widget {index} (progress): missing required 'label' field"
        if 'value' not in widget:
            return f"Widget {index} (progress): missing required 'value' field"

    elif widget_type == 'text':
        if 'content' not in widget:
            return f"Widget {index} (text): missing required 'content' field"

    elif widget_type == 'markdown':
        if 'content' not in widget:
            return f"Widget {index} (markdown): missing required 'content' field"

    elif widget_type == 'table':
        if 'columns' not in widget:
            return f"Widget {index} (table): missing required 'columns' field"
        if 'rows' not in widget:
            return f"Widget {index} (table): missing required 'rows' field"

    elif widget_type == 'list':
        if 'items' not in widget:
            return f"Widget {index} (list): missing required 'items' field"

    elif widget_type == 'link':
        if 'label' not in widget:
            return f"Widget {index} (link): missing required 'label' field"
        if 'url' not in widget:
            return f"Widget {index} (link): missing required 'url' field"

    elif widget_type == 'image':
        if 'src' not in widget:
            return f"Widget {index} (image): missing required 'src' field"
        if 'alt' not in widget:
            return f"Widget {index} (image): missing required 'alt' field"

    return None


def validate_section(section: Dict[str, Any], index: int) -> List[str]:
    """Validate a section. Returns list of error messages."""
    errors = []

    if 'widgets' not in section:
        errors.append(f"Section {index}: missing required 'widgets' field")
        return errors

    if not isinstance(section['widgets'], list):
        errors.append(f"Section {index}: 'widgets' must be a list")
        return errors

    # Validate layout
    layout = section.get('layout', 'grid')
    if layout not in ['grid', 'list']:
        errors.append(f"Section {index}: invalid layout '{layout}'. Valid values: grid, list")

    # Validate columns
    columns = section.get('columns', 3)
    if not isinstance(columns, int) or columns < 1 or columns > 4:
        errors.append(f"Section {index}: columns must be 1-4, got {columns}")

    # Validate widgets
    for widget_index, widget in enumerate(section['widgets']):
        error = validate_widget(widget, widget_index)
        if error:
            errors.append(f"Section {index}, {error}")

    return errors


def validate_dashboard(config: Dict[str, Any]) -> List[str]:
    """Validate dashboard configuration. Returns list of error messages."""
    errors = []

    if 'title' not in config:
        errors.append("Missing required 'title' field")

    if 'sections' not in config:
        errors.append("Missing required 'sections' field")
        return errors

    if not isinstance(config['sections'], list):
        errors.append("'sections' must be a list")
        return errors

    # Validate refresh interval
    refresh = config.get('refresh', 30)
    if not isinstance(refresh, (int, float)) or refresh < 5:
        errors.append(f"'refresh' must be a number >= 5, got {refresh}")

    # Validate each section
    for section_index, section in enumerate(config['sections']):
        section_errors = validate_section(section, section_index)
        errors.extend(section_errors)

    return errors


@router.get("/api/dashboard")
async def get_dashboard():
    """
    Get agent dashboard configuration.

    Returns:
    - has_dashboard: Whether agent has a dashboard.yaml file
    - config: Parsed dashboard configuration (title, sections, widgets)
    - last_modified: File modification timestamp
    - error: Error message if parsing failed
    """
    dashboard_path = get_dashboard_path()

    if not dashboard_path.exists():
        return {
            "has_dashboard": False,
            "config": None,
            "last_modified": None,
            "error": "No dashboard.yaml found at /home/developer/dashboard.yaml"
        }

    try:
        # Read and parse YAML
        content = dashboard_path.read_text()
        config = yaml.safe_load(content)

        if config is None:
            return {
                "has_dashboard": False,
                "config": None,
                "last_modified": None,
                "error": "dashboard.yaml is empty"
            }

        # Validate configuration
        errors = validate_dashboard(config)
        if errors:
            return {
                "has_dashboard": False,
                "config": None,
                "last_modified": None,
                "error": f"Validation errors: {'; '.join(errors)}"
            }

        # Get file modification time
        stat = dashboard_path.stat()
        last_modified = datetime.fromtimestamp(stat.st_mtime).isoformat()

        # Ensure defaults
        if 'refresh' not in config:
            config['refresh'] = 30

        return {
            "has_dashboard": True,
            "config": config,
            "last_modified": last_modified,
            "error": None
        }

    except yaml.YAMLError as e:
        # Get line number from YAML error if available
        error_msg = str(e)
        if hasattr(e, 'problem_mark') and e.problem_mark:
            mark = e.problem_mark
            error_msg = f"YAML parse error at line {mark.line + 1}, column {mark.column + 1}: {e.problem}"

        return {
            "has_dashboard": False,
            "config": None,
            "last_modified": None,
            "error": error_msg
        }
    except Exception as e:
        logger.error(f"Failed to read dashboard.yaml: {e}")
        return {
            "has_dashboard": False,
            "config": None,
            "last_modified": None,
            "error": f"Failed to read dashboard.yaml: {str(e)}"
        }
