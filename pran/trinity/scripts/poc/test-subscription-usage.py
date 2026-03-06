#!/usr/bin/env python3
"""
POC: Test OAuth usage endpoint for Claude Max/Pro subscriptions

This tests the undocumented endpoint that Claude Code uses internally
to check subscription usage limits.

Endpoint: GET https://api.anthropic.com/api/oauth/usage
Auth: Bearer token from claudeAiOauth.accessToken in .credentials.json
"""
import json
import os
import subprocess
import sys

import httpx


def get_credentials_from_keychain():
    """Get credentials from macOS Keychain (where Claude Code stores them)."""
    try:
        result = subprocess.run(
            ["security", "find-generic-password", "-s", "Claude Code-credentials", "-w"],
            capture_output=True,
            text=True
        )
        if result.returncode == 0:
            return json.loads(result.stdout.strip())
    except Exception as e:
        print(f"  Could not read from Keychain: {e}")
    return None


def get_credentials_from_file(path: str = None):
    """Get credentials from .credentials.json file."""
    if path is None:
        path = os.path.expanduser("~/.claude/.credentials.json")

    if os.path.exists(path):
        with open(path, "r") as f:
            return json.load(f)
    return None


def extract_access_token(credentials: dict) -> str | None:
    """Extract the OAuth access token from credentials."""
    if not credentials:
        return None

    # Try different possible locations
    if "claudeAiOauth" in credentials:
        oauth = credentials["claudeAiOauth"]
        if isinstance(oauth, dict) and "accessToken" in oauth:
            return oauth["accessToken"]

    # Direct accessToken
    if "accessToken" in credentials:
        return credentials["accessToken"]

    return None


def check_subscription_usage(access_token: str) -> dict | None:
    """Call the OAuth usage endpoint to get subscription limits."""

    headers = {
        "Authorization": f"Bearer {access_token}",
        "anthropic-beta": "oauth-2025-04-20",
        "User-Agent": "claude-code/2.0.32",
        "Accept": "application/json, text/plain, */*",
        "Content-Type": "application/json",
    }

    try:
        with httpx.Client() as client:
            response = client.get(
                "https://api.anthropic.com/api/oauth/usage",
                headers=headers,
                timeout=30.0
            )

            print(f"\n  Status: {response.status_code}")

            if response.status_code == 200:
                return response.json()
            else:
                print(f"  Error response: {response.text[:500]}")
                return None

    except Exception as e:
        print(f"  Request failed: {e}")
        return None


def main():
    print("=" * 60)
    print("POC: Claude Subscription Usage Check")
    print("=" * 60)

    # Try to get credentials
    print("\n1. Looking for OAuth credentials...")

    # Try keychain first (macOS)
    credentials = get_credentials_from_keychain()
    if credentials:
        print("   Found credentials in macOS Keychain")
    else:
        # Try file
        credentials = get_credentials_from_file()
        if credentials:
            print("   Found credentials in ~/.claude/.credentials.json")
        else:
            print("   No credentials found!")
            print("\n   To use this tool, you need either:")
            print("   - Claude Code installed with active login (Keychain)")
            print("   - Or a .credentials.json file")
            return False

    # Extract access token
    print("\n2. Extracting OAuth access token...")
    access_token = extract_access_token(credentials)

    if not access_token:
        print("   Could not extract accessToken from credentials")
        print(f"   Credential keys: {list(credentials.keys())}")
        return False

    print(f"   Found token (ends with ...{access_token[-8:]})")

    # Call usage endpoint
    print("\n3. Calling OAuth usage endpoint...")
    usage_data = check_subscription_usage(access_token)

    if usage_data:
        print("\n" + "=" * 60)
        print("SUCCESS! Usage data retrieved:")
        print("=" * 60)
        print(json.dumps(usage_data, indent=2))

        # Parse and display nicely
        print("\n" + "-" * 60)
        print("PARSED USAGE:")
        print("-" * 60)

        if "five_hour" in usage_data:
            fh = usage_data["five_hour"]
            print(f"  5-Hour Window:")
            print(f"    Utilization: {fh.get('utilization', 'N/A')}%")
            print(f"    Resets at:   {fh.get('resets_at', 'N/A')}")

        if "seven_day" in usage_data:
            sd = usage_data["seven_day"]
            print(f"\n  7-Day Window:")
            print(f"    Utilization: {sd.get('utilization', 'N/A')}%")
            print(f"    Resets at:   {sd.get('resets_at', 'N/A')}")

        return True
    else:
        print("\n   Failed to retrieve usage data")
        return False


if __name__ == "__main__":
    success = main()
    print("\n" + "=" * 60)
    if success:
        print("POC VALIDATED: We can programmatically check subscription usage!")
    else:
        print("POC FAILED: Could not retrieve subscription usage")
    print("=" * 60)
    sys.exit(0 if success else 1)
