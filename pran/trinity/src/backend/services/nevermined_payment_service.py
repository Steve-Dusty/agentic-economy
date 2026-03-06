"""
Nevermined x402 payment service (NVM-001).

Handles verify/settle lifecycle via the payments-py SDK.
All SDK calls are sync internally, so they are wrapped in asyncio.to_thread().
"""

import asyncio
import logging
from typing import Optional

from db_models import NeverminedConfig, NeverminedPaymentResult

logger = logging.getLogger(__name__)

# Lazy SDK availability check
NEVERMINED_AVAILABLE = False
try:
    from payments_py.payments import Payments
    from payments_py.common.types import PaymentOptions
    from payments_py.x402.helpers import build_payment_required
    NEVERMINED_AVAILABLE = True
except ImportError:
    logger.warning("payments-py not installed — Nevermined endpoints will return 501")


class NeverminedPaymentService:
    """Handles x402 payment verification and settlement via Nevermined SDK."""

    def _get_payments_client(self, nvm_api_key: str, nvm_environment: str):
        """Create a Payments instance for the given credentials.

        The nvm_api_key must be in "env:jwt" format (e.g. "sandbox:eyJhbGci...").
        If the stored key lacks the environment prefix, it is prepended.
        """
        if not NEVERMINED_AVAILABLE:
            raise RuntimeError("payments-py SDK is not installed")

        # Ensure key is in "env:jwt" format
        if ":" not in nvm_api_key:
            nvm_api_key = f"{nvm_environment}:{nvm_api_key}"

        return Payments.get_instance(PaymentOptions(
            nvm_api_key=nvm_api_key,
            environment=nvm_environment,
        ))

    def build_402_response(self, config: NeverminedConfig, base_url: str = "") -> dict:
        """Build the 402 Payment Required response body.

        Returns a dict suitable for JSON serialization in the 402 response.
        """
        if not NEVERMINED_AVAILABLE:
            raise RuntimeError("payments-py SDK is not installed")

        endpoint = f"{base_url}/api/paid/{config.agent_name}/chat"

        # Determine network from environment
        network_map = {
            "sandbox": "eip155:84532",       # Base Sepolia testnet
            "staging_sandbox": "eip155:84532",
            "live": "eip155:8453",            # Base mainnet
            "staging_live": "eip155:8453",
            "custom": "eip155:84532",
        }
        network = network_map.get(config.nvm_environment, "eip155:84532")

        payment_required = build_payment_required(
            plan_id=config.nvm_plan_id,
            endpoint=endpoint,
            agent_id=config.nvm_agent_id,
            http_verb="POST",
            network=network,
        )

        return payment_required.model_dump(by_alias=True)

    async def verify_payment(
        self,
        nvm_api_key: str,
        nvm_environment: str,
        config: NeverminedConfig,
        access_token: str,
        base_url: str = "",
    ) -> NeverminedPaymentResult:
        """Verify a payment token before processing a request.

        Does NOT burn credits — only checks validity and balance.
        Timeout: 15 seconds.
        """
        if not NEVERMINED_AVAILABLE:
            raise RuntimeError("payments-py SDK is not installed")

        try:
            payments = self._get_payments_client(nvm_api_key, nvm_environment)

            endpoint = f"{base_url}/api/paid/{config.agent_name}/chat"
            network_map = {
                "sandbox": "eip155:84532",
                "staging_sandbox": "eip155:84532",
                "live": "eip155:8453",
                "staging_live": "eip155:8453",
                "custom": "eip155:84532",
            }
            network = network_map.get(config.nvm_environment, "eip155:84532")

            payment_required = build_payment_required(
                plan_id=config.nvm_plan_id,
                endpoint=endpoint,
                agent_id=config.nvm_agent_id,
                http_verb="POST",
                network=network,
            )

            result = await asyncio.wait_for(
                asyncio.to_thread(
                    payments.facilitator.verify_permissions,
                    payment_required,
                    access_token,
                ),
                timeout=15.0,
            )

            return NeverminedPaymentResult(
                success=result.is_valid,
                payer=result.payer,
                agent_request_id=result.agent_request_id,
                error=result.invalid_reason if not result.is_valid else None,
            )
        except asyncio.TimeoutError:
            logger.error(f"Nevermined verify timeout for agent {config.agent_name}")
            return NeverminedPaymentResult(
                success=False,
                error="Payment verification timed out",
            )
        except Exception as e:
            logger.error(f"Nevermined verify error for agent {config.agent_name}: {e}")
            return NeverminedPaymentResult(
                success=False,
                error=str(e),
            )

    async def settle_payment(
        self,
        nvm_api_key: str,
        nvm_environment: str,
        config: NeverminedConfig,
        access_token: str,
        agent_request_id: Optional[str] = None,
        base_url: str = "",
    ) -> NeverminedPaymentResult:
        """Settle a payment after successful task execution.

        Burns credits on-chain. Retries up to 3 times with exponential backoff.
        Timeout per attempt: 30 seconds.
        """
        if not NEVERMINED_AVAILABLE:
            raise RuntimeError("payments-py SDK is not installed")

        payments = self._get_payments_client(nvm_api_key, nvm_environment)

        endpoint = f"{base_url}/api/paid/{config.agent_name}/chat"
        network_map = {
            "sandbox": "eip155:84532",
            "staging_sandbox": "eip155:84532",
            "live": "eip155:8453",
            "staging_live": "eip155:8453",
            "custom": "eip155:84532",
        }
        network = network_map.get(config.nvm_environment, "eip155:84532")

        payment_required = build_payment_required(
            plan_id=config.nvm_plan_id,
            endpoint=endpoint,
            agent_id=config.nvm_agent_id,
            http_verb="POST",
            network=network,
        )

        last_error = None
        for attempt in range(3):
            try:
                result = await asyncio.wait_for(
                    asyncio.to_thread(
                        payments.facilitator.settle_permissions,
                        payment_required,
                        access_token,
                        None,  # max_amount
                        agent_request_id,
                    ),
                    timeout=30.0,
                )

                if result.success:
                    return NeverminedPaymentResult(
                        success=True,
                        payer=result.payer,
                        credits_redeemed=result.credits_redeemed,
                        remaining_balance=result.remaining_balance,
                        tx_hash=result.transaction,
                    )
                else:
                    return NeverminedPaymentResult(
                        success=False,
                        payer=result.payer,
                        error=result.error_reason,
                    )

            except asyncio.TimeoutError:
                last_error = "Settlement timed out"
                logger.warning(
                    f"Nevermined settle timeout for agent {config.agent_name} "
                    f"(attempt {attempt + 1}/3)"
                )
            except Exception as e:
                last_error = str(e)
                logger.warning(
                    f"Nevermined settle error for agent {config.agent_name} "
                    f"(attempt {attempt + 1}/3): {e}"
                )

            # Exponential backoff: 1s, 2s, 4s
            if attempt < 2:
                await asyncio.sleep(2 ** attempt)

        # All retries exhausted
        logger.error(
            f"Nevermined settle failed after 3 attempts for agent {config.agent_name}: {last_error}"
        )
        return NeverminedPaymentResult(
            success=False,
            error=f"Settlement failed after 3 attempts: {last_error}",
        )


# ---------------------------------------------------------------------------
# Singleton
# ---------------------------------------------------------------------------

_nevermined_payment_service: Optional[NeverminedPaymentService] = None


def get_nevermined_payment_service() -> NeverminedPaymentService:
    """Get the global NeverminedPaymentService instance."""
    global _nevermined_payment_service
    if _nevermined_payment_service is None:
        _nevermined_payment_service = NeverminedPaymentService()
    return _nevermined_payment_service
