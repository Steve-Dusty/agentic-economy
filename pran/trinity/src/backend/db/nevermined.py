"""
Nevermined payment configuration database operations (NVM-001).

Manages per-agent Nevermined x402 payment configuration and payment audit logs.
NVM_API_KEY is encrypted using the same AES-256-GCM system as subscription tokens.
"""

import uuid
from datetime import datetime
from typing import Optional, List

from .connection import get_db_connection
from db_models import NeverminedConfig, NeverminedPaymentLog


class NeverminedOperations:
    """Database operations for Nevermined payment configuration and logging."""

    def __init__(self, encryption_service=None):
        self._encryption_service = encryption_service

    def _get_encryption_service(self):
        """Get or create the encryption service (lazy loading)."""
        if self._encryption_service is None:
            from services.credential_encryption import get_credential_encryption_service
            self._encryption_service = get_credential_encryption_service()
        return self._encryption_service

    @staticmethod
    def _row_to_config(row) -> NeverminedConfig:
        """Convert a database row to a NeverminedConfig model."""
        row_dict = dict(row) if row else {}
        return NeverminedConfig(
            id=row_dict["id"],
            agent_name=row_dict["agent_name"],
            nvm_environment=row_dict["nvm_environment"],
            nvm_agent_id=row_dict["nvm_agent_id"],
            nvm_plan_id=row_dict["nvm_plan_id"],
            credits_per_request=row_dict["credits_per_request"],
            enabled=bool(row_dict["enabled"]),
            created_at=row_dict["created_at"],
            updated_at=row_dict["updated_at"],
        )

    @staticmethod
    def _row_to_payment_log(row) -> NeverminedPaymentLog:
        """Convert a database row to a NeverminedPaymentLog model."""
        row_dict = dict(row) if row else {}
        return NeverminedPaymentLog(
            id=row_dict["id"],
            agent_name=row_dict["agent_name"],
            execution_id=row_dict.get("execution_id"),
            action=row_dict["action"],
            subscriber_address=row_dict.get("subscriber_address"),
            credits_amount=row_dict.get("credits_amount"),
            tx_hash=row_dict.get("tx_hash"),
            remaining_balance=row_dict.get("remaining_balance"),
            success=bool(row_dict["success"]),
            error=row_dict.get("error"),
            created_at=row_dict["created_at"],
        )

    # =========================================================================
    # Config CRUD
    # =========================================================================

    def create_or_update_config(
        self,
        agent_name: str,
        nvm_api_key: str,
        nvm_environment: str,
        nvm_agent_id: str,
        nvm_plan_id: str,
        credits_per_request: int = 1,
    ) -> NeverminedConfig:
        """Create or update Nevermined config for an agent. Encrypts the API key."""
        encryption_service = self._get_encryption_service()
        encrypted = encryption_service.encrypt({"nvm_api_key": nvm_api_key})
        now = datetime.utcnow().isoformat()

        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT id FROM nevermined_agent_config WHERE agent_name = ?",
                (agent_name,)
            )
            existing = cursor.fetchone()

            if existing:
                config_id = existing["id"]
                cursor.execute("""
                    UPDATE nevermined_agent_config
                    SET encrypted_credentials = ?,
                        nvm_environment = ?,
                        nvm_agent_id = ?,
                        nvm_plan_id = ?,
                        credits_per_request = ?,
                        updated_at = ?
                    WHERE id = ?
                """, (encrypted, nvm_environment, nvm_agent_id, nvm_plan_id,
                      credits_per_request, now, config_id))
            else:
                config_id = str(uuid.uuid4())
                cursor.execute("""
                    INSERT INTO nevermined_agent_config
                    (id, agent_name, encrypted_credentials, nvm_environment, nvm_agent_id,
                     nvm_plan_id, credits_per_request, enabled, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, 0, ?, ?)
                """, (config_id, agent_name, encrypted, nvm_environment, nvm_agent_id,
                      nvm_plan_id, credits_per_request, now, now))

            conn.commit()

            cursor.execute(
                "SELECT * FROM nevermined_agent_config WHERE id = ?",
                (config_id,)
            )
            return self._row_to_config(cursor.fetchone())

    def get_config(self, agent_name: str) -> Optional[NeverminedConfig]:
        """Get Nevermined config for an agent (without decrypted key)."""
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM nevermined_agent_config WHERE agent_name = ?",
                (agent_name,)
            )
            row = cursor.fetchone()
            return self._row_to_config(row) if row else None

    def get_config_with_key(self, agent_name: str) -> Optional[dict]:
        """Get config + decrypted NVM_API_KEY. Internal use only."""
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM nevermined_agent_config WHERE agent_name = ?",
                (agent_name,)
            )
            row = cursor.fetchone()
            if not row:
                return None

            config = self._row_to_config(row)
            encryption_service = self._get_encryption_service()
            decrypted = encryption_service.decrypt(row["encrypted_credentials"])
            nvm_api_key = decrypted.get("nvm_api_key", "")

            return {
                "config": config,
                "nvm_api_key": nvm_api_key,
            }

    def delete_config(self, agent_name: str) -> bool:
        """Delete Nevermined config for an agent."""
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "DELETE FROM nevermined_agent_config WHERE agent_name = ?",
                (agent_name,)
            )
            conn.commit()
            return cursor.rowcount > 0

    def set_enabled(self, agent_name: str, enabled: bool) -> bool:
        """Enable or disable Nevermined payments for an agent."""
        now = datetime.utcnow().isoformat()
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE nevermined_agent_config
                SET enabled = ?, updated_at = ?
                WHERE agent_name = ?
            """, (1 if enabled else 0, now, agent_name))
            conn.commit()
            return cursor.rowcount > 0

    def is_nevermined_enabled(self, agent_name: str) -> bool:
        """Fast check if Nevermined is enabled for an agent."""
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT enabled FROM nevermined_agent_config WHERE agent_name = ?",
                (agent_name,)
            )
            row = cursor.fetchone()
            return bool(row["enabled"]) if row else False

    # =========================================================================
    # Payment Log
    # =========================================================================

    def log_payment(
        self,
        agent_name: str,
        action: str,
        success: bool,
        execution_id: Optional[str] = None,
        subscriber_address: Optional[str] = None,
        credits_amount: Optional[int] = None,
        tx_hash: Optional[str] = None,
        remaining_balance: Optional[int] = None,
        error: Optional[str] = None,
    ) -> NeverminedPaymentLog:
        """Log a payment action (verify, settle, settle_failed, reject)."""
        log_id = str(uuid.uuid4())
        now = datetime.utcnow().isoformat()

        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO nevermined_payment_log
                (id, agent_name, execution_id, action, subscriber_address,
                 credits_amount, tx_hash, remaining_balance, success, error, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (log_id, agent_name, execution_id, action, subscriber_address,
                  credits_amount, tx_hash, remaining_balance,
                  1 if success else 0, error, now))
            conn.commit()

            cursor.execute(
                "SELECT * FROM nevermined_payment_log WHERE id = ?",
                (log_id,)
            )
            return self._row_to_payment_log(cursor.fetchone())

    def get_payment_log(
        self,
        agent_name: str,
        limit: int = 50,
    ) -> List[NeverminedPaymentLog]:
        """Get payment log entries for an agent, newest first."""
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM nevermined_payment_log
                WHERE agent_name = ?
                ORDER BY created_at DESC
                LIMIT ?
            """, (agent_name, limit))
            return [self._row_to_payment_log(row) for row in cursor.fetchall()]

    def get_settlement_failures(self, limit: int = 50) -> List[NeverminedPaymentLog]:
        """Get all failed settlements across all agents (admin view)."""
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM nevermined_payment_log
                WHERE action = 'settle_failed'
                ORDER BY created_at DESC
                LIMIT ?
            """, (limit,))
            return [self._row_to_payment_log(row) for row in cursor.fetchall()]

    def get_payment_log_entry(self, log_id: str) -> Optional[NeverminedPaymentLog]:
        """Get a single payment log entry by ID."""
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM nevermined_payment_log WHERE id = ?",
                (log_id,)
            )
            row = cursor.fetchone()
            return self._row_to_payment_log(row) if row else None
