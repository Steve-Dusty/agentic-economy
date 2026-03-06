#!/usr/bin/env python3
"""Call a paid Nevermined agent with x402 payment flow."""

import argparse
import json
import os
import sys

import requests
from payments_py import Payments, PaymentOptions


def get_payments():
    return Payments.get_instance(
        PaymentOptions(
            nvm_api_key=os.environ["NVM_API_KEY"],
            environment=os.environ.get("NVM_ENVIRONMENT", "sandbox"),
            app_id="nevermined-purchaser",
            version="1.0.0",
        )
    )


def call_agent(url, message, plan_id, agent_id, timeout=60):
    payments = get_payments()

    # Check balance
    balance = payments.plans.get_plan_balance(plan_id)
    print(f"Credits remaining: {balance.balance}")
    if balance.balance <= 0:
        print("ERROR: No credits remaining. Purchase more credits first.")
        sys.exit(1)

    # Get access token
    print("Getting payment token...")
    access = payments.x402.get_x402_access_token(plan_id, agent_id)
    token = access["accessToken"]

    # Call the agent
    print(f"Calling {url}...")
    headers = {
        "payment-signature": token,
        "Content-Type": "application/json",
    }
    payload = {"message": message}

    response = requests.post(url, headers=headers, json=payload, timeout=timeout)

    print(f"Status: {response.status_code}")

    try:
        data = response.json()
        print(json.dumps(data, indent=2))

        # Report payment status
        payment = data.get("payment", {})
        if payment.get("settled"):
            print(f"\nPayment settled successfully.")
        elif data.get("status") == "failed":
            print(f"\nExecution failed - no charge. Reason: {payment.get('reason', 'unknown')}")

        return data
    except Exception:
        print(f"Raw response: {response.text}")
        return response.text


def check_balance(plan_id):
    payments = get_payments()
    balance = payments.plans.get_plan_balance(plan_id)
    print(f"Plan: {balance.plan_name}")
    print(f"Balance: {balance.balance} credits")
    print(f"Subscriber: {balance.is_subscriber}")
    return balance


def main():
    parser = argparse.ArgumentParser(description="Call a paid Nevermined agent")
    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # call command
    call_parser = subparsers.add_parser("call", help="Call a paid agent")
    call_parser.add_argument("--url", required=True, help="Agent endpoint URL")
    call_parser.add_argument("--message", required=True, help="Message to send")
    call_parser.add_argument("--plan-id", default=None, help="Override plan ID")
    call_parser.add_argument("--agent-id", default=None, help="Override agent ID")
    call_parser.add_argument("--timeout", type=int, default=60, help="Request timeout in seconds")

    # balance command
    balance_parser = subparsers.add_parser("balance", help="Check credit balance")
    balance_parser.add_argument("--plan-id", default=None, help="Override plan ID")

    args = parser.parse_args()

    # Fall back to positional-style usage if no subcommand
    if args.command is None:
        # Support legacy: pay_and_call.py --url X --message Y
        parser.add_argument("--url", required=True)
        parser.add_argument("--message", required=True)
        parser.add_argument("--plan-id", default=None)
        parser.add_argument("--agent-id", default=None)
        parser.add_argument("--timeout", type=int, default=60)
        args = parser.parse_args()
        args.command = "call"

    plan_id = getattr(args, "plan_id", None) or os.environ["NVM_PLAN_ID"]
    agent_id = getattr(args, "agent_id", None) or os.environ.get("NVM_AGENT_ID", "")

    if args.command == "call":
        call_agent(args.url, args.message, plan_id, agent_id, args.timeout)
    elif args.command == "balance":
        check_balance(plan_id)


if __name__ == "__main__":
    main()
