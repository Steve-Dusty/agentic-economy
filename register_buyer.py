"""Register buyer agent on the Nevermined marketplace."""
import os
from dotenv import load_dotenv
from payments_py import Payments, PaymentOptions
from payments_py.common.types import AgentMetadata, AgentAPIAttributes, PlanMetadata, Endpoint
from payments_py.plans import get_free_price_config, get_fixed_credits_config

load_dotenv()

BUYER_URL = os.environ.get("BUYER_URL", "http://localhost:8000")


def main():
    payments = Payments.get_instance(
        PaymentOptions(
            nvm_api_key=os.environ["NVM_API_KEY"],
            environment="sandbox",
        )
    )

    wallet = payments.account_address
    print(f"Wallet address: {wallet}")

    print("\n--- Registering Buyer Agent ---")
    result = payments.agents.register_agent_and_plan(
        agent_metadata=AgentMetadata(
            name="AI Research Buyer Agent",
            description="Autonomous buyer agent — discovers sellers on the Nevermined marketplace, purchases AI research data via x402 payments, and tracks spending with budget controls.",
            tags=["ai", "research", "buyer", "x402", "marketplace"],
        ),
        agent_api=AgentAPIAttributes(
            endpoints=[
                Endpoint(verb="POST", url=f"{BUYER_URL}/api/query"),
            ],
            agent_definition_url=f"{BUYER_URL}/pricing",
        ),
        plan_metadata=PlanMetadata(
            name="Buyer Agent Plan",
            description="50 free queries to the buyer agent",
        ),
        price_config=get_free_price_config(),
        credits_config=get_fixed_credits_config(credits_granted=50),
        access_limit="credits",
    )

    agent_id = result["agentId"]
    plan_id = result["planId"]

    print(f"  Agent ID: {agent_id}")
    print(f"  Plan ID:  {plan_id}")

    # Append to .env
    env_lines = [
        f"\n# --- Buyer Agent (registered {__import__('datetime').date.today()}) ---",
        f"NVM_BUYER_AGENT_ID={agent_id}",
        f"NVM_BUYER_PLAN_ID={plan_id}",
    ]
    with open(".env", "a") as f:
        f.write("\n".join(env_lines) + "\n")

    print(f"\n=== Buyer agent registered! .env updated. ===")
    print(f"  NVM_BUYER_AGENT_ID={agent_id}")
    print(f"  NVM_BUYER_PLAN_ID={plan_id}")


if __name__ == "__main__":
    main()
