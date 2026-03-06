"""
Process Template Service

Manages process templates for quick-start workflows.
Reference: BACKLOG_ADVANCED.md - E12-01, E12-02

Part of the Process-Driven Platform feature.
"""

import logging
import os
import sqlite3
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, List
import yaml

logger = logging.getLogger(__name__)


@dataclass
class ProcessTemplateInfo:
    """Summary info for a process template."""
    id: str
    name: str
    display_name: str
    description: str
    category: str
    complexity: str
    version: str
    author: str
    tags: List[str] = field(default_factory=list)
    step_types_used: List[str] = field(default_factory=list)
    source: str = "bundled"  # bundled | user | community

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "display_name": self.display_name,
            "description": self.description,
            "category": self.category,
            "complexity": self.complexity,
            "version": self.version,
            "author": self.author,
            "tags": self.tags,
            "step_types_used": self.step_types_used,
            "source": self.source,
        }


@dataclass
class ProcessTemplate:
    """Full process template with definition."""
    info: ProcessTemplateInfo
    definition_yaml: str
    use_cases: List[str] = field(default_factory=list)
    created_at: Optional[datetime] = None
    created_by: Optional[str] = None

    def to_dict(self) -> dict:
        result = self.info.to_dict()
        result["definition_yaml"] = self.definition_yaml
        result["use_cases"] = self.use_cases
        result["created_at"] = self.created_at.isoformat() if self.created_at else None
        result["created_by"] = self.created_by
        return result


class ProcessTemplateService:
    """
    Service for managing process templates.

    Templates can come from:
    - Bundled templates in config/process-templates/
    - User-created templates stored in database
    - Community templates (future)
    """

    def __init__(
        self,
        templates_dir: Optional[str] = None,
        db_path: Optional[str] = None,
    ):
        # Bundled templates directory
        if templates_dir is None:
            # Try container path first, then local
            container_path = Path("/agent-configs/process-templates")
            local_path = Path("./config/process-templates")
            if container_path.exists():
                templates_dir = str(container_path)
            else:
                templates_dir = str(local_path)

        self._templates_dir = Path(templates_dir)

        # Database for user templates
        if db_path is None:
            db_path = os.getenv(
                "TRINITY_DB_PATH",
                str(Path.home() / "trinity-data" / "trinity.db")
            ).replace(".db", "_templates.db")
        self._db_path = db_path
        self._ensure_tables()

    def _ensure_tables(self):
        """Create database tables for user templates."""
        db_dir = os.path.dirname(self._db_path)
        if db_dir:  # Only create dir if path has a directory component
            os.makedirs(db_dir, exist_ok=True)
        conn = sqlite3.connect(self._db_path)
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS process_templates (
                id TEXT PRIMARY KEY,
                name TEXT UNIQUE NOT NULL,
                display_name TEXT,
                description TEXT,
                category TEXT DEFAULT 'general',
                complexity TEXT DEFAULT 'simple',
                version TEXT DEFAULT '1.0.0',
                author TEXT,
                tags TEXT,
                step_types_used TEXT,
                use_cases TEXT,
                definition_yaml TEXT NOT NULL,
                created_by TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)

        conn.commit()
        conn.close()

    # =========================================================================
    # Template Listing
    # =========================================================================

    def list_templates(
        self,
        category: Optional[str] = None,
        source: Optional[str] = None,
    ) -> List[ProcessTemplateInfo]:
        """
        List all available templates.

        Args:
            category: Filter by category (business, devops, analytics, etc.)
            source: Filter by source (bundled, user)

        Returns:
            List of template info summaries
        """
        templates = []

        # Load bundled templates
        if source is None or source == "bundled":
            templates.extend(self._load_bundled_templates(category))

        # Load user templates
        if source is None or source == "user":
            templates.extend(self._load_user_templates(category))

        # Sort by display name
        templates.sort(key=lambda t: t.display_name)

        return templates

    def _load_bundled_templates(
        self,
        category: Optional[str] = None,
    ) -> List[ProcessTemplateInfo]:
        """Load templates from the bundled templates directory."""
        templates = []

        if not self._templates_dir.exists():
            logger.debug(f"Templates directory not found: {self._templates_dir}")
            return templates

        for template_path in self._templates_dir.iterdir():
            if not template_path.is_dir():
                continue

            template_yaml = template_path / "template.yaml"
            if not template_yaml.exists():
                continue

            try:
                with open(template_yaml) as f:
                    data = yaml.safe_load(f)

                # Filter by category
                template_category = data.get("category", "general")
                if category and template_category != category:
                    continue

                info = ProcessTemplateInfo(
                    id=f"process:{template_path.name}",
                    name=data.get("name", template_path.name),
                    display_name=data.get("display_name", template_path.name),
                    description=data.get("description", ""),
                    category=template_category,
                    complexity=data.get("complexity", "simple"),
                    version=data.get("version", "1.0.0"),
                    author=data.get("author", "Trinity"),
                    tags=data.get("tags", []),
                    step_types_used=data.get("step_types_used", []),
                    source="bundled",
                )
                templates.append(info)

            except Exception as e:
                logger.warning(f"Failed to load template {template_path}: {e}")

        return templates

    def _load_user_templates(
        self,
        category: Optional[str] = None,
    ) -> List[ProcessTemplateInfo]:
        """Load user-created templates from database."""
        templates = []

        conn = sqlite3.connect(self._db_path)
        cursor = conn.cursor()

        query = "SELECT * FROM process_templates"
        params = []

        if category:
            query += " WHERE category = ?"
            params.append(category)

        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()

        for row in rows:
            info = ProcessTemplateInfo(
                id=f"user:{row[1]}",  # user:name
                name=row[1],
                display_name=row[2] or row[1],
                description=row[3] or "",
                category=row[4] or "general",
                complexity=row[5] or "simple",
                version=row[6] or "1.0.0",
                author=row[7] or "",
                tags=yaml.safe_load(row[8]) if row[8] else [],
                step_types_used=yaml.safe_load(row[9]) if row[9] else [],
                source="user",
            )
            templates.append(info)

        return templates

    # =========================================================================
    # Template Retrieval
    # =========================================================================

    def get_template(self, template_id: str) -> Optional[ProcessTemplate]:
        """
        Get a template by ID.

        Args:
            template_id: Template ID (e.g., "process:order-fulfillment" or "user:my-template")

        Returns:
            Full template with definition, or None if not found
        """
        if template_id.startswith("process:"):
            return self._get_bundled_template(template_id[8:])
        elif template_id.startswith("user:"):
            return self._get_user_template(template_id[5:])
        else:
            # Try both
            template = self._get_bundled_template(template_id)
            if not template:
                template = self._get_user_template(template_id)
            return template

    def _get_bundled_template(self, name: str) -> Optional[ProcessTemplate]:
        """Get a bundled template by name."""
        template_path = self._templates_dir / name

        if not template_path.exists():
            return None

        template_yaml = template_path / "template.yaml"
        definition_yaml = template_path / "definition.yaml"

        if not template_yaml.exists():
            return None

        try:
            with open(template_yaml) as f:
                data = yaml.safe_load(f)

            # Load definition
            definition_content = ""
            if definition_yaml.exists():
                with open(definition_yaml) as f:
                    definition_content = f.read()
            elif "definition" in data:
                definition_content = data["definition"]

            info = ProcessTemplateInfo(
                id=f"process:{name}",
                name=data.get("name", name),
                display_name=data.get("display_name", name),
                description=data.get("description", ""),
                category=data.get("category", "general"),
                complexity=data.get("complexity", "simple"),
                version=data.get("version", "1.0.0"),
                author=data.get("author", "Trinity"),
                tags=data.get("tags", []),
                step_types_used=data.get("step_types_used", []),
                source="bundled",
            )

            return ProcessTemplate(
                info=info,
                definition_yaml=definition_content,
                use_cases=data.get("use_cases", []),
            )

        except Exception as e:
            logger.error(f"Failed to load template {name}: {e}")
            return None

    def _get_user_template(self, name: str) -> Optional[ProcessTemplate]:
        """Get a user-created template by name."""
        conn = sqlite3.connect(self._db_path)
        cursor = conn.cursor()

        cursor.execute(
            "SELECT * FROM process_templates WHERE name = ?",
            (name,)
        )
        row = cursor.fetchone()
        conn.close()

        if not row:
            return None

        info = ProcessTemplateInfo(
            id=f"user:{row[1]}",
            name=row[1],
            display_name=row[2] or row[1],
            description=row[3] or "",
            category=row[4] or "general",
            complexity=row[5] or "simple",
            version=row[6] or "1.0.0",
            author=row[7] or "",
            tags=yaml.safe_load(row[8]) if row[8] else [],
            step_types_used=yaml.safe_load(row[9]) if row[9] else [],
            source="user",
        )

        return ProcessTemplate(
            info=info,
            definition_yaml=row[11],  # definition_yaml column
            use_cases=yaml.safe_load(row[10]) if row[10] else [],
            created_by=row[12],
            created_at=datetime.fromisoformat(row[13]) if row[13] else None,
        )

    # =========================================================================
    # Template Creation (User Templates)
    # =========================================================================

    def create_template(
        self,
        name: str,
        definition_yaml: str,
        display_name: Optional[str] = None,
        description: Optional[str] = None,
        category: str = "general",
        complexity: str = "simple",
        tags: Optional[List[str]] = None,
        use_cases: Optional[List[str]] = None,
        created_by: Optional[str] = None,
    ) -> ProcessTemplate:
        """
        Create a new user template.

        Args:
            name: Unique template name (slug)
            definition_yaml: Process definition YAML content
            display_name: Human-readable name
            description: Template description
            category: Template category
            complexity: Complexity level
            tags: List of tags
            use_cases: Example use cases
            created_by: User who created the template

        Returns:
            Created template

        Raises:
            ValueError: If template name already exists
        """
        conn = sqlite3.connect(self._db_path)
        cursor = conn.cursor()

        # Check if name exists
        cursor.execute("SELECT 1 FROM process_templates WHERE name = ?", (name,))
        if cursor.fetchone():
            conn.close()
            raise ValueError(f"Template with name '{name}' already exists")

        template_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()

        # Analyze definition to extract step types
        step_types = []
        try:
            definition = yaml.safe_load(definition_yaml)
            steps = definition.get("steps", [])
            step_types = list(set(s.get("type", "") for s in steps if s.get("type")))
        except Exception:
            pass

        cursor.execute("""
            INSERT INTO process_templates
            (id, name, display_name, description, category, complexity, version, author,
             tags, step_types_used, use_cases, definition_yaml, created_by, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            template_id, name, display_name or name, description or "", category, complexity,
            "1.0.0", created_by or "User", yaml.dump(tags or []), yaml.dump(step_types),
            yaml.dump(use_cases or []), definition_yaml, created_by, now, now,
        ))

        conn.commit()
        conn.close()

        logger.info(f"Created process template: {name}")

        return self._get_user_template(name)

    def delete_template(self, name: str) -> bool:
        """Delete a user-created template."""
        conn = sqlite3.connect(self._db_path)
        cursor = conn.cursor()

        cursor.execute("DELETE FROM process_templates WHERE name = ?", (name,))
        deleted = cursor.rowcount > 0

        conn.commit()
        conn.close()

        if deleted:
            logger.info(f"Deleted process template: {name}")

        return deleted
