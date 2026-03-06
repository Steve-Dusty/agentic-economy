"""
Cost Alert Service

Monitors process execution costs and generates alerts when thresholds are exceeded.
Reference: BACKLOG_ADVANCED.md - E11-03

Part of the Process-Driven Platform feature.
"""

import logging
import sqlite3
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from enum import Enum
from typing import Optional, List
from pathlib import Path
import os

logger = logging.getLogger(__name__)


class ThresholdType(str, Enum):
    """Types of cost thresholds."""
    PER_EXECUTION = "per_execution"
    DAILY = "daily"
    WEEKLY = "weekly"


class AlertSeverity(str, Enum):
    """Alert severity levels."""
    WARNING = "warning"
    CRITICAL = "critical"


class AlertStatus(str, Enum):
    """Alert status."""
    ACTIVE = "active"
    DISMISSED = "dismissed"


@dataclass
class CostThreshold:
    """A cost threshold configuration."""
    id: str
    process_id: str
    threshold_type: ThresholdType
    threshold_amount: Decimal
    currency: str = "USD"
    enabled: bool = True
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "process_id": self.process_id,
            "threshold_type": self.threshold_type.value,
            "threshold_amount": float(self.threshold_amount),
            "currency": self.currency,
            "enabled": self.enabled,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: dict) -> "CostThreshold":
        return cls(
            id=data["id"],
            process_id=data["process_id"],
            threshold_type=ThresholdType(data["threshold_type"]),
            threshold_amount=Decimal(str(data["threshold_amount"])),
            currency=data.get("currency", "USD"),
            enabled=bool(data.get("enabled", True)),
            created_at=datetime.fromisoformat(data["created_at"]) if data.get("created_at") else datetime.now(timezone.utc),
            updated_at=datetime.fromisoformat(data["updated_at"]) if data.get("updated_at") else datetime.now(timezone.utc),
        )


@dataclass
class CostAlert:
    """A triggered cost alert."""
    id: str
    process_id: str
    process_name: str
    execution_id: Optional[str]
    threshold_type: ThresholdType
    threshold_amount: Decimal
    actual_amount: Decimal
    currency: str = "USD"
    severity: AlertSeverity = AlertSeverity.WARNING
    status: AlertStatus = AlertStatus.ACTIVE
    message: str = ""
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    dismissed_at: Optional[datetime] = None
    dismissed_by: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "process_id": self.process_id,
            "process_name": self.process_name,
            "execution_id": self.execution_id,
            "threshold_type": self.threshold_type.value,
            "threshold_amount": float(self.threshold_amount),
            "actual_amount": float(self.actual_amount),
            "currency": self.currency,
            "severity": self.severity.value,
            "status": self.status.value,
            "message": self.message,
            "created_at": self.created_at.isoformat(),
            "dismissed_at": self.dismissed_at.isoformat() if self.dismissed_at else None,
            "dismissed_by": self.dismissed_by,
        }

    @classmethod
    def from_row(cls, row: tuple) -> "CostAlert":
        return cls(
            id=row[0],
            process_id=row[1],
            process_name=row[2],
            execution_id=row[3],
            threshold_type=ThresholdType(row[4]),
            threshold_amount=Decimal(str(row[5])),
            actual_amount=Decimal(str(row[6])),
            currency=row[7] or "USD",
            severity=AlertSeverity(row[8]) if row[8] else AlertSeverity.WARNING,
            status=AlertStatus(row[9]) if row[9] else AlertStatus.ACTIVE,
            message=row[10] or "",
            created_at=datetime.fromisoformat(row[11]) if row[11] else datetime.now(timezone.utc),
            dismissed_at=datetime.fromisoformat(row[12]) if row[12] else None,
            dismissed_by=row[13],
        )


class CostAlertService:
    """
    Service for managing cost thresholds and alerts.

    Provides:
    - Threshold configuration per process
    - Alert generation when costs exceed thresholds
    - Alert management (list, dismiss)
    """

    def __init__(self, db_path: Optional[str] = None):
        if db_path is None:
            db_path = os.getenv(
                "TRINITY_DB_PATH",
                str(Path.home() / "trinity-data" / "trinity.db")
            ).replace(".db", "_alerts.db")
        self._db_path = db_path
        self._ensure_tables()

    def _ensure_tables(self):
        """Create database tables if they don't exist."""
        conn = sqlite3.connect(self._db_path)
        cursor = conn.cursor()

        # Cost thresholds table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS cost_thresholds (
                id TEXT PRIMARY KEY,
                process_id TEXT NOT NULL,
                threshold_type TEXT NOT NULL,
                threshold_amount REAL NOT NULL,
                currency TEXT DEFAULT 'USD',
                enabled INTEGER DEFAULT 1,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                UNIQUE(process_id, threshold_type)
            )
        """)

        # Cost alerts table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS cost_alerts (
                id TEXT PRIMARY KEY,
                process_id TEXT NOT NULL,
                process_name TEXT NOT NULL,
                execution_id TEXT,
                threshold_type TEXT NOT NULL,
                threshold_amount REAL NOT NULL,
                actual_amount REAL NOT NULL,
                currency TEXT DEFAULT 'USD',
                severity TEXT DEFAULT 'warning',
                status TEXT DEFAULT 'active',
                message TEXT,
                created_at TEXT NOT NULL,
                dismissed_at TEXT,
                dismissed_by TEXT
            )
        """)

        cursor.execute("CREATE INDEX IF NOT EXISTS idx_alerts_process ON cost_alerts(process_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_alerts_status ON cost_alerts(status)")

        conn.commit()
        conn.close()

    # =========================================================================
    # Threshold Management
    # =========================================================================

    def get_thresholds(self, process_id: str) -> List[CostThreshold]:
        """Get all thresholds for a process."""
        conn = sqlite3.connect(self._db_path)
        cursor = conn.cursor()

        cursor.execute(
            "SELECT * FROM cost_thresholds WHERE process_id = ?",
            (process_id,)
        )
        rows = cursor.fetchall()
        conn.close()

        thresholds = []
        for row in rows:
            thresholds.append(CostThreshold(
                id=row[0],
                process_id=row[1],
                threshold_type=ThresholdType(row[2]),
                threshold_amount=Decimal(str(row[3])),
                currency=row[4] or "USD",
                enabled=bool(row[5]),
                created_at=datetime.fromisoformat(row[6]) if row[6] else datetime.now(timezone.utc),
                updated_at=datetime.fromisoformat(row[7]) if row[7] else datetime.now(timezone.utc),
            ))

        return thresholds

    def set_threshold(
        self,
        process_id: str,
        threshold_type: ThresholdType,
        amount: Decimal,
        enabled: bool = True,
    ) -> CostThreshold:
        """Set or update a threshold for a process."""
        conn = sqlite3.connect(self._db_path)
        cursor = conn.cursor()

        now = datetime.now(timezone.utc).isoformat()
        threshold_id = str(uuid.uuid4())

        # Check if threshold exists
        cursor.execute(
            "SELECT id FROM cost_thresholds WHERE process_id = ? AND threshold_type = ?",
            (process_id, threshold_type.value)
        )
        existing = cursor.fetchone()

        if existing:
            threshold_id = existing[0]
            cursor.execute("""
                UPDATE cost_thresholds
                SET threshold_amount = ?, enabled = ?, updated_at = ?
                WHERE id = ?
            """, (float(amount), int(enabled), now, threshold_id))
        else:
            cursor.execute("""
                INSERT INTO cost_thresholds
                (id, process_id, threshold_type, threshold_amount, currency, enabled, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (threshold_id, process_id, threshold_type.value, float(amount), "USD", int(enabled), now, now))

        conn.commit()
        conn.close()

        return CostThreshold(
            id=threshold_id,
            process_id=process_id,
            threshold_type=threshold_type,
            threshold_amount=amount,
            enabled=enabled,
            updated_at=datetime.fromisoformat(now),
        )

    def delete_threshold(self, process_id: str, threshold_type: ThresholdType) -> bool:
        """Delete a threshold."""
        conn = sqlite3.connect(self._db_path)
        cursor = conn.cursor()

        cursor.execute(
            "DELETE FROM cost_thresholds WHERE process_id = ? AND threshold_type = ?",
            (process_id, threshold_type.value)
        )
        deleted = cursor.rowcount > 0

        conn.commit()
        conn.close()

        return deleted

    # =========================================================================
    # Alert Checking
    # =========================================================================

    def check_execution_cost(
        self,
        process_id: str,
        process_name: str,
        execution_id: str,
        cost: Decimal,
    ) -> Optional[CostAlert]:
        """
        Check if an execution cost exceeds the per-execution threshold.

        Called when an execution completes.
        """
        thresholds = self.get_thresholds(process_id)

        for threshold in thresholds:
            if not threshold.enabled:
                continue

            if threshold.threshold_type != ThresholdType.PER_EXECUTION:
                continue

            if cost > threshold.threshold_amount:
                # Determine severity
                overage = cost / threshold.threshold_amount
                severity = AlertSeverity.CRITICAL if overage > 2 else AlertSeverity.WARNING

                alert = self._create_alert(
                    process_id=process_id,
                    process_name=process_name,
                    execution_id=execution_id,
                    threshold=threshold,
                    actual_amount=cost,
                    severity=severity,
                    message=f"Execution cost ${cost:.2f} exceeded threshold ${threshold.threshold_amount:.2f}",
                )
                return alert

        return None

    def check_daily_costs(
        self,
        process_id: str,
        process_name: str,
        daily_cost: Decimal,
    ) -> Optional[CostAlert]:
        """
        Check if daily costs exceed the daily threshold.
        """
        thresholds = self.get_thresholds(process_id)

        for threshold in thresholds:
            if not threshold.enabled:
                continue

            if threshold.threshold_type != ThresholdType.DAILY:
                continue

            if daily_cost > threshold.threshold_amount:
                # Check if we already have an alert for today
                today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
                existing = self._get_alert_for_day(process_id, ThresholdType.DAILY, today)
                if existing:
                    return None

                severity = AlertSeverity.CRITICAL if daily_cost > threshold.threshold_amount * 2 else AlertSeverity.WARNING

                alert = self._create_alert(
                    process_id=process_id,
                    process_name=process_name,
                    execution_id=None,
                    threshold=threshold,
                    actual_amount=daily_cost,
                    severity=severity,
                    message=f"Daily cost ${daily_cost:.2f} exceeded threshold ${threshold.threshold_amount:.2f}",
                )
                return alert

        return None

    def check_weekly_costs(
        self,
        process_id: str,
        process_name: str,
        weekly_cost: Decimal,
    ) -> Optional[CostAlert]:
        """
        Check if weekly costs exceed the weekly threshold.
        """
        thresholds = self.get_thresholds(process_id)

        for threshold in thresholds:
            if not threshold.enabled:
                continue

            if threshold.threshold_type != ThresholdType.WEEKLY:
                continue

            if weekly_cost > threshold.threshold_amount:
                # Check if we already have an alert for this week
                week_start = (datetime.now(timezone.utc) - timedelta(days=datetime.now(timezone.utc).weekday())).strftime("%Y-%m-%d")
                existing = self._get_alert_for_week(process_id, ThresholdType.WEEKLY, week_start)
                if existing:
                    return None

                severity = AlertSeverity.CRITICAL if weekly_cost > threshold.threshold_amount * 2 else AlertSeverity.WARNING

                alert = self._create_alert(
                    process_id=process_id,
                    process_name=process_name,
                    execution_id=None,
                    threshold=threshold,
                    actual_amount=weekly_cost,
                    severity=severity,
                    message=f"Weekly cost ${weekly_cost:.2f} exceeded threshold ${threshold.threshold_amount:.2f}",
                )
                return alert

        return None

    def _create_alert(
        self,
        process_id: str,
        process_name: str,
        execution_id: Optional[str],
        threshold: CostThreshold,
        actual_amount: Decimal,
        severity: AlertSeverity,
        message: str,
    ) -> CostAlert:
        """Create and save a new alert."""
        alert = CostAlert(
            id=str(uuid.uuid4()),
            process_id=process_id,
            process_name=process_name,
            execution_id=execution_id,
            threshold_type=threshold.threshold_type,
            threshold_amount=threshold.threshold_amount,
            actual_amount=actual_amount,
            severity=severity,
            message=message,
        )

        conn = sqlite3.connect(self._db_path)
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO cost_alerts
            (id, process_id, process_name, execution_id, threshold_type, threshold_amount,
             actual_amount, currency, severity, status, message, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            alert.id, alert.process_id, alert.process_name, alert.execution_id,
            alert.threshold_type.value, float(alert.threshold_amount), float(alert.actual_amount),
            alert.currency, alert.severity.value, alert.status.value, alert.message,
            alert.created_at.isoformat(),
        ))

        conn.commit()
        conn.close()

        logger.warning(f"Cost alert created: {message}")
        return alert

    def _get_alert_for_day(
        self,
        process_id: str,
        threshold_type: ThresholdType,
        date: str,
    ) -> Optional[CostAlert]:
        """Check if an alert already exists for a specific day."""
        conn = sqlite3.connect(self._db_path)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT * FROM cost_alerts
            WHERE process_id = ? AND threshold_type = ? AND date(created_at) = ?
            LIMIT 1
        """, (process_id, threshold_type.value, date))

        row = cursor.fetchone()
        conn.close()

        return CostAlert.from_row(row) if row else None

    def _get_alert_for_week(
        self,
        process_id: str,
        threshold_type: ThresholdType,
        week_start: str,
    ) -> Optional[CostAlert]:
        """Check if an alert already exists for a specific week."""
        conn = sqlite3.connect(self._db_path)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT * FROM cost_alerts
            WHERE process_id = ? AND threshold_type = ? AND date(created_at) >= ?
            LIMIT 1
        """, (process_id, threshold_type.value, week_start))

        row = cursor.fetchone()
        conn.close()

        return CostAlert.from_row(row) if row else None

    # =========================================================================
    # Alert Management
    # =========================================================================

    def get_alerts(
        self,
        status: Optional[AlertStatus] = None,
        process_id: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[CostAlert]:
        """Get alerts with optional filters."""
        conn = sqlite3.connect(self._db_path)
        cursor = conn.cursor()

        query = "SELECT * FROM cost_alerts WHERE 1=1"
        params = []

        if status:
            query += " AND status = ?"
            params.append(status.value)

        if process_id:
            query += " AND process_id = ?"
            params.append(process_id)

        query += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])

        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()

        return [CostAlert.from_row(row) for row in rows]

    def get_active_alerts_count(self) -> int:
        """Get count of active alerts."""
        conn = sqlite3.connect(self._db_path)
        cursor = conn.cursor()

        cursor.execute(
            "SELECT COUNT(*) FROM cost_alerts WHERE status = ?",
            (AlertStatus.ACTIVE.value,)
        )
        count = cursor.fetchone()[0]
        conn.close()

        return count

    def dismiss_alert(self, alert_id: str, dismissed_by: str) -> bool:
        """Dismiss an alert."""
        conn = sqlite3.connect(self._db_path)
        cursor = conn.cursor()

        now = datetime.now(timezone.utc).isoformat()
        cursor.execute("""
            UPDATE cost_alerts
            SET status = ?, dismissed_at = ?, dismissed_by = ?
            WHERE id = ?
        """, (AlertStatus.DISMISSED.value, now, dismissed_by, alert_id))

        success = cursor.rowcount > 0
        conn.commit()
        conn.close()

        return success

    def get_alert(self, alert_id: str) -> Optional[CostAlert]:
        """Get a single alert by ID."""
        conn = sqlite3.connect(self._db_path)
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM cost_alerts WHERE id = ?", (alert_id,))
        row = cursor.fetchone()
        conn.close()

        return CostAlert.from_row(row) if row else None
