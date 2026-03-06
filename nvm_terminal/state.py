"""Shared application state."""
import os
from dataclasses import dataclass, field
from dotenv import load_dotenv
from payments_py import Payments, PaymentOptions


@dataclass
class AppState:
    payments: Payments
    agents_cache: dict = field(default_factory=dict)
    transactions: list = field(default_factory=list)
    config: dict = field(default_factory=dict)
    auto_mode: bool = False
    auto_stop: bool = False  # signal to stop auto mode


def init_state() -> AppState:
    """Load .env, init Payments SDK, return AppState."""
    load_dotenv()

    nvm_api_key = os.environ["NVM_API_KEY"]
    nvm_env = os.getenv("NVM_ENVIRONMENT", "sandbox")

    payments = Payments.get_instance(
        PaymentOptions(nvm_api_key=nvm_api_key, environment=nvm_env)
    )

    config = {
        "nvm_api_key": nvm_api_key,
        "nvm_environment": nvm_env,
        "plan_id": os.environ.get("NVM_PLAN_ID", ""),
        "agent_id": os.environ.get("NVM_AGENT_ID", ""),
        "plan_id_crypto": os.environ.get("NVM_PLAN_ID_CRYPTO", ""),
        "agent_id_crypto": os.environ.get("NVM_AGENT_ID_CRYPTO", ""),
        "plan_id_fiat": os.environ.get("NVM_PLAN_ID_FIAT", ""),
        "buyer_agent_id": os.environ.get("NVM_BUYER_AGENT_ID", ""),
        "wallet": os.environ.get("USDC_WALLET", ""),
        "seller_url": os.getenv("SELLER_URL", "http://localhost:3000"),
        "max_daily_spend": int(os.getenv("MAX_DAILY_SPEND", "50")),
        "max_per_request": int(os.getenv("MAX_PER_REQUEST", "10")),
        "openai_api_key": os.environ.get("OPENAI_API_KEY", ""),
        "zeroclick_api_key": os.environ.get("ZEROCLICK_API_KEY", ""),
        "haist_url": os.getenv("HAIST_URL", "http://localhost:3000"),
    }

    return AppState(payments=payments, config=config)
