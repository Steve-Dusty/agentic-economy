"""
Dashboard history operations for Trinity platform (DASH-001).

Handles capturing and querying historical dashboard widget values for:
- Sparkline visualization in the UI
- Trend calculation (up/down/stable)
- Platform metrics injection
"""

import logging
import secrets
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any

from .connection import get_db_connection
from utils.helpers import utc_now_iso

logger = logging.getLogger(__name__)


class DashboardHistoryOperations:
    """Dashboard history database operations."""

    @staticmethod
    def _generate_id() -> str:
        """Generate a unique ID."""
        return secrets.token_urlsafe(16)

    def capture_dashboard_snapshot(
        self,
        agent_name: str,
        config: Dict[str, Any],
        dashboard_mtime: str
    ) -> int:
        """Capture snapshot of all trackable widget values from a dashboard config.

        Trackable widgets are: metric, progress, status (with numeric values).
        Each widget is stored with a key generated from its position or explicit ID.

        Args:
            agent_name: Name of the agent
            config: Dashboard configuration dict (with sections/widgets)
            dashboard_mtime: Modification time of the dashboard.yaml file

        Returns:
            Number of widget values captured
        """
        if not config or "sections" not in config:
            return 0

        captured_at = utc_now_iso()
        captured_count = 0

        with get_db_connection() as conn:
            cursor = conn.cursor()

            for section_idx, section in enumerate(config.get("sections", [])):
                for widget_idx, widget in enumerate(section.get("widgets", [])):
                    widget_type = widget.get("type")

                    # Only track widgets with meaningful values
                    if widget_type not in ("metric", "progress", "status"):
                        continue

                    # Generate widget key: use explicit id if provided, else position-based
                    widget_key = widget.get("id") or f"s{section_idx}_w{widget_idx}"
                    widget_label = widget.get("label", "")
                    value = widget.get("value")

                    # Extract numeric and text values
                    value_numeric = None
                    value_text = None

                    if value is not None:
                        if isinstance(value, (int, float)):
                            value_numeric = float(value)
                        elif isinstance(value, str):
                            # Try to parse numeric from string (e.g., "1,234" or "95%")
                            value_text = value
                            try:
                                # Remove common formatting
                                cleaned = value.replace(",", "").replace("%", "").replace("$", "").strip()
                                value_numeric = float(cleaned)
                            except (ValueError, TypeError):
                                pass

                    # Skip if no value to store
                    if value_numeric is None and value_text is None:
                        continue

                    record_id = self._generate_id()
                    cursor.execute("""
                        INSERT INTO agent_dashboard_values (
                            id, agent_name, widget_key, widget_label, widget_type,
                            value_numeric, value_text, dashboard_mtime, captured_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        record_id, agent_name, widget_key, widget_label, widget_type,
                        value_numeric, value_text, dashboard_mtime, captured_at
                    ))
                    captured_count += 1

            conn.commit()

        if captured_count > 0:
            logger.debug(f"Captured {captured_count} dashboard values for agent {agent_name}")

        return captured_count

    def get_widget_history(
        self,
        agent_name: str,
        widget_key: str,
        hours: int = 24,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Get historical values for a specific widget.

        Args:
            agent_name: Name of the agent
            widget_key: Widget identifier (explicit id or position-based)
            hours: How many hours of history to retrieve
            limit: Maximum number of records

        Returns:
            List of dicts with 't' (ISO timestamp) and 'v' (numeric value)
        """
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT captured_at, value_numeric, value_text
                FROM agent_dashboard_values
                WHERE agent_name = ? AND widget_key = ?
                AND captured_at > datetime('now', ? || ' hours')
                ORDER BY captured_at ASC
                LIMIT ?
            """, (agent_name, widget_key, f"-{hours}", limit))

            results = []
            for row in cursor.fetchall():
                value = row["value_numeric"]
                if value is None and row["value_text"]:
                    # Use text value if no numeric
                    value = row["value_text"]
                results.append({
                    "t": row["captured_at"],
                    "v": value
                })

            return results

    def get_all_widget_history(
        self,
        agent_name: str,
        hours: int = 24
    ) -> Dict[str, List[Dict[str, Any]]]:
        """Get history for all widgets of an agent, keyed by widget_key.

        Args:
            agent_name: Name of the agent
            hours: How many hours of history to retrieve

        Returns:
            Dict mapping widget_key to list of {t, v} values
        """
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT widget_key, captured_at, value_numeric, value_text
                FROM agent_dashboard_values
                WHERE agent_name = ?
                AND captured_at > datetime('now', ? || ' hours')
                ORDER BY widget_key, captured_at ASC
            """, (agent_name, f"-{hours}"))

            results: Dict[str, List[Dict[str, Any]]] = {}
            for row in cursor.fetchall():
                widget_key = row["widget_key"]
                if widget_key not in results:
                    results[widget_key] = []

                value = row["value_numeric"]
                if value is None and row["value_text"]:
                    value = row["value_text"]

                results[widget_key].append({
                    "t": row["captured_at"],
                    "v": value
                })

            return results

    def calculate_widget_stats(
        self,
        values: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Calculate statistics from a list of historical values.

        Args:
            values: List of {t, v} dicts from get_widget_history

        Returns:
            Dict with min, max, avg, trend, trend_percent
        """
        if not values:
            return {
                "min": None,
                "max": None,
                "avg": None,
                "trend": "stable",
                "trend_percent": 0
            }

        # Extract numeric values only
        numeric_values = [v["v"] for v in values if isinstance(v.get("v"), (int, float))]

        if not numeric_values:
            return {
                "min": None,
                "max": None,
                "avg": None,
                "trend": "stable",
                "trend_percent": 0
            }

        min_val = min(numeric_values)
        max_val = max(numeric_values)
        avg_val = sum(numeric_values) / len(numeric_values)

        # Calculate trend: compare first half avg to second half avg
        trend = "stable"
        trend_percent = 0

        if len(numeric_values) >= 2:
            mid = len(numeric_values) // 2
            first_half_avg = sum(numeric_values[:mid]) / mid if mid > 0 else numeric_values[0]
            second_half_avg = sum(numeric_values[mid:]) / (len(numeric_values) - mid)

            if first_half_avg > 0:
                trend_percent = ((second_half_avg - first_half_avg) / first_half_avg) * 100

                if trend_percent > 5:
                    trend = "up"
                elif trend_percent < -5:
                    trend = "down"

        return {
            "min": round(min_val, 2),
            "max": round(max_val, 2),
            "avg": round(avg_val, 2),
            "trend": trend,
            "trend_percent": round(trend_percent, 1)
        }

    def get_last_captured_mtime(self, agent_name: str) -> Optional[str]:
        """Get the most recent dashboard_mtime that was captured for an agent.

        Used for change detection - only capture new snapshots when mtime changes.

        Args:
            agent_name: Name of the agent

        Returns:
            Last captured dashboard_mtime or None if no history
        """
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT dashboard_mtime FROM agent_dashboard_values
                WHERE agent_name = ?
                ORDER BY captured_at DESC
                LIMIT 1
            """, (agent_name,))
            row = cursor.fetchone()
            return row["dashboard_mtime"] if row else None

    def cleanup_old_snapshots(self, days: int = 30) -> int:
        """Delete dashboard value records older than specified days.

        Args:
            days: Number of days to retain

        Returns:
            Number of records deleted
        """
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                DELETE FROM agent_dashboard_values
                WHERE captured_at < datetime('now', ? || ' days')
            """, (f"-{days}",))
            conn.commit()
            deleted = cursor.rowcount
            if deleted > 0:
                logger.info(f"Cleaned up {deleted} old dashboard value records")
            return deleted

    def delete_agent_dashboard_history(self, agent_name: str) -> int:
        """Delete all dashboard history for an agent (when agent is deleted).

        Args:
            agent_name: Name of the agent

        Returns:
            Number of records deleted
        """
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                DELETE FROM agent_dashboard_values WHERE agent_name = ?
            """, (agent_name,))
            conn.commit()
            return cursor.rowcount
