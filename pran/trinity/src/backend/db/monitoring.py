"""
Monitoring database operations for agent health checks.

Handles storage and retrieval of health check results, alert cooldowns,
and historical data for trend analysis.
"""

import json
import secrets
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any

from .connection import get_db_connection
from utils.helpers import utc_now_iso


class MonitoringOperations:
    """Database operations for agent health monitoring."""

    # =========================================================================
    # Health Check Records
    # =========================================================================

    def create_health_check(
        self,
        agent_name: str,
        check_type: str,
        status: str,
        docker_metrics: Optional[Dict] = None,
        network_metrics: Optional[Dict] = None,
        business_metrics: Optional[Dict] = None,
        error_message: Optional[str] = None,
    ) -> str:
        """
        Create a new health check record.

        Args:
            agent_name: Name of the agent
            check_type: Type of check (docker, network, business, aggregate)
            status: Health status (healthy, degraded, unhealthy, critical)
            docker_metrics: Docker layer metrics
            network_metrics: Network layer metrics
            business_metrics: Business logic metrics
            error_message: Optional error message

        Returns:
            ID of created record
        """
        check_id = f"hc_{secrets.token_urlsafe(12)}"
        now = utc_now_iso()

        # Extract metrics from dicts
        docker = docker_metrics or {}
        network = network_metrics or {}
        business = business_metrics or {}

        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO agent_health_checks (
                    id, agent_name, check_type, status,
                    container_status, cpu_percent, memory_percent, memory_mb,
                    restart_count, oom_killed,
                    reachable, latency_ms,
                    runtime_available, claude_available, context_percent,
                    active_executions, error_rate,
                    error_message, checked_at, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                check_id,
                agent_name,
                check_type,
                status,
                # Docker metrics
                docker.get("container_status"),
                docker.get("cpu_percent"),
                docker.get("memory_percent"),
                docker.get("memory_mb"),
                docker.get("restart_count"),
                1 if docker.get("oom_killed") else 0 if docker.get("oom_killed") is False else None,
                # Network metrics
                1 if network.get("reachable") else 0 if network.get("reachable") is False else None,
                network.get("latency_ms"),
                # Business metrics
                1 if business.get("runtime_available") else 0 if business.get("runtime_available") is False else None,
                1 if business.get("claude_available") else 0 if business.get("claude_available") is False else None,
                business.get("context_percent"),
                business.get("active_executions"),
                business.get("error_rate"),
                # Common fields
                error_message,
                now,
                now,
            ))
            conn.commit()

        return check_id

    def get_latest_health_check(
        self,
        agent_name: str,
        check_type: str = "aggregate"
    ) -> Optional[Dict]:
        """Get the most recent health check for an agent."""
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM agent_health_checks
                WHERE agent_name = ? AND check_type = ?
                ORDER BY checked_at DESC
                LIMIT 1
            """, (agent_name, check_type))
            row = cursor.fetchone()
            if not row:
                return None
            return self._row_to_health_check(cursor, row)

    def get_agent_health_history(
        self,
        agent_name: str,
        check_type: str = "aggregate",
        hours: int = 24,
        limit: int = 100
    ) -> List[Dict]:
        """Get health check history for an agent."""
        since = (datetime.utcnow() - timedelta(hours=hours)).isoformat() + "Z"

        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM agent_health_checks
                WHERE agent_name = ? AND check_type = ? AND checked_at >= ?
                ORDER BY checked_at DESC
                LIMIT ?
            """, (agent_name, check_type, since, limit))
            rows = cursor.fetchall()
            return [self._row_to_health_check(cursor, row) for row in rows]

    def get_all_latest_health_checks(
        self,
        agent_names: Optional[List[str]] = None,
        check_type: str = "aggregate"
    ) -> Dict[str, Dict]:
        """
        Get the latest health check for multiple agents.

        Returns:
            Dict mapping agent_name -> health check record
        """
        with get_db_connection() as conn:
            cursor = conn.cursor()

            if agent_names:
                placeholders = ",".join("?" * len(agent_names))
                cursor.execute(f"""
                    SELECT h1.* FROM agent_health_checks h1
                    INNER JOIN (
                        SELECT agent_name, MAX(checked_at) as max_checked
                        FROM agent_health_checks
                        WHERE check_type = ? AND agent_name IN ({placeholders})
                        GROUP BY agent_name
                    ) h2 ON h1.agent_name = h2.agent_name AND h1.checked_at = h2.max_checked
                    WHERE h1.check_type = ?
                """, [check_type] + agent_names + [check_type])
            else:
                cursor.execute("""
                    SELECT h1.* FROM agent_health_checks h1
                    INNER JOIN (
                        SELECT agent_name, MAX(checked_at) as max_checked
                        FROM agent_health_checks
                        WHERE check_type = ?
                        GROUP BY agent_name
                    ) h2 ON h1.agent_name = h2.agent_name AND h1.checked_at = h2.max_checked
                    WHERE h1.check_type = ?
                """, (check_type, check_type))

            rows = cursor.fetchall()
            return {
                self._row_to_health_check(cursor, row)["agent_name"]: self._row_to_health_check(cursor, row)
                for row in rows
            }

    def get_health_summary(
        self,
        agent_names: Optional[List[str]] = None
    ) -> Dict[str, int]:
        """
        Get summary counts of health statuses.

        Returns:
            Dict with keys: healthy, degraded, unhealthy, critical, unknown
        """
        latest = self.get_all_latest_health_checks(agent_names, "aggregate")

        summary = {"healthy": 0, "degraded": 0, "unhealthy": 0, "critical": 0, "unknown": 0}
        for check in latest.values():
            status = check.get("status", "unknown")
            if status in summary:
                summary[status] += 1
            else:
                summary["unknown"] += 1

        return summary

    def calculate_uptime_percent(
        self,
        agent_name: str,
        hours: int = 24
    ) -> Optional[float]:
        """Calculate uptime percentage for an agent over the specified period."""
        history = self.get_agent_health_history(agent_name, "aggregate", hours, limit=1000)
        if not history:
            return None

        healthy_count = sum(1 for h in history if h["status"] in ["healthy", "degraded"])
        return (healthy_count / len(history)) * 100 if history else None

    def calculate_avg_latency(
        self,
        agent_name: str,
        hours: int = 24
    ) -> Optional[float]:
        """Calculate average latency for an agent over the specified period."""
        history = self.get_agent_health_history(agent_name, "network", hours, limit=1000)
        if not history:
            return None

        latencies = [h["latency_ms"] for h in history if h.get("latency_ms") is not None]
        return sum(latencies) / len(latencies) if latencies else None

    def cleanup_old_records(self, days: int = 7) -> int:
        """
        Delete health check records older than specified days.

        Returns:
            Number of deleted records
        """
        cutoff = (datetime.utcnow() - timedelta(days=days)).isoformat() + "Z"

        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                DELETE FROM agent_health_checks
                WHERE checked_at < ?
            """, (cutoff,))
            deleted = cursor.rowcount
            conn.commit()

        return deleted

    # =========================================================================
    # Alert Cooldowns
    # =========================================================================

    def get_cooldown(
        self,
        agent_name: str,
        condition: str
    ) -> Optional[str]:
        """Get the last alert timestamp for a condition."""
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT last_alert_at FROM monitoring_alert_cooldowns
                WHERE agent_name = ? AND condition = ?
            """, (agent_name, condition))
            row = cursor.fetchone()
            return row[0] if row else None

    def set_cooldown(
        self,
        agent_name: str,
        condition: str
    ) -> None:
        """Set or update the cooldown timestamp for a condition."""
        now = utc_now_iso()
        cooldown_id = f"cd_{secrets.token_urlsafe(8)}"

        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO monitoring_alert_cooldowns (id, agent_name, condition, last_alert_at)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(agent_name, condition) DO UPDATE SET last_alert_at = ?
            """, (cooldown_id, agent_name, condition, now, now))
            conn.commit()

    def clear_cooldown(
        self,
        agent_name: str,
        condition: str
    ) -> bool:
        """Clear a cooldown entry. Returns True if entry existed."""
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                DELETE FROM monitoring_alert_cooldowns
                WHERE agent_name = ? AND condition = ?
            """, (agent_name, condition))
            deleted = cursor.rowcount > 0
            conn.commit()
            return deleted

    def is_in_cooldown(
        self,
        agent_name: str,
        condition: str,
        cooldown_seconds: int
    ) -> bool:
        """Check if a condition is still in cooldown period."""
        last_alert = self.get_cooldown(agent_name, condition)
        if not last_alert:
            return False

        try:
            last_alert_time = datetime.fromisoformat(last_alert.replace("Z", "+00:00"))
            cooldown_end = last_alert_time + timedelta(seconds=cooldown_seconds)
            now = datetime.utcnow().replace(tzinfo=last_alert_time.tzinfo)
            return now < cooldown_end
        except (ValueError, TypeError):
            return False

    def cleanup_cooldowns(self, agent_name: Optional[str] = None) -> int:
        """
        Clear all cooldowns for an agent (or all agents if not specified).

        Returns:
            Number of deleted records
        """
        with get_db_connection() as conn:
            cursor = conn.cursor()
            if agent_name:
                cursor.execute("""
                    DELETE FROM monitoring_alert_cooldowns
                    WHERE agent_name = ?
                """, (agent_name,))
            else:
                cursor.execute("DELETE FROM monitoring_alert_cooldowns")
            deleted = cursor.rowcount
            conn.commit()
            return deleted

    # =========================================================================
    # Helper Methods
    # =========================================================================

    def _row_to_health_check(self, cursor, row) -> Dict[str, Any]:
        """Convert a database row to a health check dict."""
        columns = [desc[0] for desc in cursor.description]
        result = dict(zip(columns, row))

        # Convert boolean fields
        for bool_field in ["oom_killed", "reachable", "runtime_available", "claude_available"]:
            if result.get(bool_field) is not None:
                result[bool_field] = bool(result[bool_field])

        return result
