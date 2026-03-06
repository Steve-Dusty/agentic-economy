"""Register seller agent with multiple payment plan types on Nevermined."""
import os
from dotenv import load_dotenv
from payments_py import Payments, PaymentOptions
from payments_py.common.types import AgentMetadata, AgentAPIAttributes, PlanMetadata, Endpoint
from payments_py.plans import (
    get_free_price_config,
    get_erc20_price_config,
    get_fiat_price_config,
    get_fixed_credits_config,
)

load_dotenv()

USDC_ADDRESS = "0x036CbD53842c5426634e7929541eC2318f3dCF7e"  # USDC on Base Sepolia
BASE_URL = os.environ.get("SELLER_URL", "http://localhost:3000")


def main():
    payments = Payments.get_instance(
        PaymentOptions(
            nvm_api_key=os.environ["NVM_API_KEY"],
            environment="sandbox",
        )
    )

    wallet = payments.account_address
    print(f"Wallet address: {wallet}")

    # --- 1. FREE plan (for testing) ---
    print("\n--- Registering FREE plan agent ---")
    free_result = payments.agents.register_agent_and_plan(
        agent_metadata=AgentMetadata(
            name="AI Research Agent (Free)",
            description="AI-powered research — free tier for testing",
            tags=["ai", "research", "free"],
        ),
        agent_api=AgentAPIAttributes(
            endpoints=[Endpoint(verb="POST", url=f"{BASE_URL}/api/ask")],
            agent_definition_url=f"{BASE_URL}/pricing",
        ),
        plan_metadata=PlanMetadata(
            name="Free Testing Plan",
            description="100 free requests for testing",
        ),
        price_config=get_free_price_config(),
        credits_config=get_fixed_credits_config(credits_granted=100),
        access_limit="credits",
    )
    print(f"  Agent ID: {free_result['agentId']}")
    print(f"  Plan ID:  {free_result['planId']}")

    # --- 2. CRYPTO (ERC-20 USDC) plan ---
    print("\n--- Registering CRYPTO (USDC) plan agent ---")
    crypto_result = payments.agents.register_agent_and_plan(
        agent_metadata=AgentMetadata(
            name="AI Research Agent (Crypto)",
            description="AI-powered research — pay with USDC",
            tags=["ai", "research", "crypto"],
        ),
        agent_api=AgentAPIAttributes(
            endpoints=[Endpoint(verb="POST", url=f"{BASE_URL}/api/ask")],
            agent_definition_url=f"{BASE_URL}/pricing",
        ),
        plan_metadata=PlanMetadata(
            name="Crypto Plan - 10 USDC",
            description="100 requests for 10 USDC",
        ),
        price_config=get_erc20_price_config(
            amount=10_000_000,  # 10 USDC (6 decimals)
            token_address=USDC_ADDRESS,
            receiver=wallet,
        ),
        credits_config=get_fixed_credits_config(credits_granted=100),
        access_limit="credits",
    )
    print(f"  Agent ID: {crypto_result['agentId']}")
    print(f"  Plan ID:  {crypto_result['planId']}")

    # --- 3. FIAT (Stripe) plan ---
    print("\n--- Registering FIAT (Stripe) plan agent ---")
    fiat_result = payments.agents.register_agent_and_plan(
        agent_metadata=AgentMetadata(
            name="AI Research Agent (Fiat)",
            description="AI-powered research — pay with credit card",
            tags=["ai", "research", "fiat"],
        ),
        agent_api=AgentAPIAttributes(
            endpoints=[Endpoint(verb="POST", url=f"{BASE_URL}/api/ask")],
            agent_definition_url=f"{BASE_URL}/pricing",
        ),
        plan_metadata=PlanMetadata(
            name="Fiat Plan - $10",
            description="100 requests for $10 USD",
        ),
        price_config=get_fiat_price_config(
            amount=1000,  # $10.00 in cents
            receiver=wallet,
        ),
        credits_config=get_fixed_credits_config(credits_granted=100),
        access_limit="credits",
    )
    print(f"  Agent ID: {fiat_result['agentId']}")
    print(f"  Plan ID:  {fiat_result['planId']}")

    # --- Save to .env (use free plan for default testing) ---
    env_lines = [
        f"\n# --- Nevermined Agent IDs (registered {__import__('datetime').date.today()}) ---",
        f"NVM_AGENT_ID={free_result['agentId']}",
        f"NVM_PLAN_ID={free_result['planId']}",
        f"NVM_AGENT_ID_CRYPTO={crypto_result['agentId']}",
        f"NVM_PLAN_ID_CRYPTO={crypto_result['planId']}",
        f"NVM_AGENT_ID_FIAT={fiat_result['agentId']}",
        f"NVM_PLAN_ID_FIAT={fiat_result['planId']}",
        "NVM_ENVIRONMENT=sandbox",
    ]
    with open(".env", "a") as f:
        f.write("\n".join(env_lines) + "\n")

    print("\n=== All 3 plans registered! .env updated. ===")
    print(f"\nDefault (free) plan for testing:")
    print(f"  NVM_AGENT_ID={free_result['agentId']}")
    print(f"  NVM_PLAN_ID={free_result['planId']}")


if __name__ == "__main__":
    main()
