#!/usr/bin/env python3
"""
Nevermined x402 Payment Demo (NVM-001)

Demonstrates the buyer-side flow for paying an agent via x402 protocol:
1. Hit paid endpoint without payment → show 402 response
2. Parse payment-required details → display plan info
3. Send authenticated request with a pre-configured subscriber token
4. Show response + payment receipt

Usage:
    # Step 1: Configure an agent with Nevermined (via UI or API)
    # Step 2: Run this script with your subscriber access token
    python scripts/poc/nevermined_demo.py --agent my-agent --token "YOUR_ACCESS_TOKEN"

    # Or just demo the 402 discovery flow (no token needed)
    python scripts/poc/nevermined_demo.py --agent my-agent
"""

import argparse
import json
import sys

import httpx

DEFAULT_BASE_URL = "http://localhost:8000"


def main():
    parser = argparse.ArgumentParser(description="Nevermined x402 Payment Demo")
    parser.add_argument("--agent", required=True, help="Agent name with Nevermined enabled")
    parser.add_argument("--token", help="x402 access token (payment-signature header)")
    parser.add_argument("--message", default="Hello, I'm paying for this!", help="Message to send")
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL, help="Trinity backend URL")
    args = parser.parse_args()

    base = args.base_url.rstrip("/")
    endpoint = f"{base}/api/paid/{args.agent}/chat"

    print(f"\n{'='*60}")
    print(f"  Nevermined x402 Payment Demo")
    print(f"  Agent: {args.agent}")
    print(f"  Endpoint: {endpoint}")
    print(f"{'='*60}\n")

    # --- Step 1: Discovery (GET /info) ---
    print("[1] Fetching agent payment info...")
    info_url = f"{base}/api/paid/{args.agent}/info"
    try:
        resp = httpx.get(info_url, timeout=10)
        if resp.status_code == 200:
            info = resp.json()
            print(f"    Plan ID: {info.get('nvm_plan_id', 'N/A')}")
            print(f"    Credits per request: {info.get('credits_per_request', 'N/A')}")
            print(f"    Payment required details:")
            print(f"    {json.dumps(info.get('payment_required', {}), indent=4)[:500]}")
        elif resp.status_code == 404:
            print(f"    Agent not found or payments not enabled.")
            sys.exit(1)
        elif resp.status_code == 501:
            print(f"    Nevermined SDK not installed on backend.")
            sys.exit(1)
        else:
            print(f"    Unexpected status: {resp.status_code}")
            print(f"    {resp.text}")
    except httpx.ConnectError:
        print(f"    Cannot connect to {base}. Is the backend running?")
        sys.exit(1)

    # --- Step 2: Request without payment → 402 ---
    print(f"\n[2] Sending request WITHOUT payment-signature header...")
    resp = httpx.post(endpoint, json={"message": args.message}, timeout=10)
    print(f"    Status: {resp.status_code}")
    if resp.status_code == 402:
        body = resp.json()
        print(f"    Response: Payment Required")
        print(f"    Credits needed: {body.get('credits_per_request', '?')}")
        print(f"    Payment details included: {'payment_required' in body}")
    else:
        print(f"    Expected 402, got {resp.status_code}: {resp.text[:200]}")

    # --- Step 3: Request with payment (if token provided) ---
    if not args.token:
        print(f"\n[3] Skipping paid request (no --token provided)")
        print(f"    To complete the demo, provide a subscriber access token:")
        print(f"    python {sys.argv[0]} --agent {args.agent} --token YOUR_TOKEN")
        return

    print(f"\n[3] Sending request WITH payment-signature header...")
    headers = {"payment-signature": args.token}
    resp = httpx.post(
        endpoint,
        json={"message": args.message},
        headers=headers,
        timeout=120,  # Task execution can take time
    )
    print(f"    Status: {resp.status_code}")

    if resp.status_code == 200:
        body = resp.json()
        print(f"    Task status: {body.get('status', 'N/A')}")
        print(f"    Execution ID: {body.get('execution_id', 'N/A')}")
        response_text = body.get("response", "")
        print(f"    Response: {response_text[:200]}{'...' if len(response_text) > 200 else ''}")
        payment = body.get("payment", {})
        if payment.get("settled"):
            print(f"\n    Payment Receipt:")
            print(f"      Credits burned: {payment.get('credits_burned', '?')}")
            print(f"      Remaining balance: {payment.get('remaining_balance', '?')}")
            print(f"      Tx hash: {payment.get('tx_hash', 'N/A')}")
        else:
            print(f"\n    Payment NOT settled: {payment.get('reason', payment.get('error', 'unknown'))}")
    elif resp.status_code == 403:
        body = resp.json()
        print(f"    Payment verification failed: {body.get('error', body.get('detail', 'unknown'))}")
    else:
        print(f"    Unexpected: {resp.text[:300]}")

    print(f"\n{'='*60}")
    print(f"  Demo complete")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()
