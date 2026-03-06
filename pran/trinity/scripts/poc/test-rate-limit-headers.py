#!/usr/bin/env python3
"""
POC: Test if Anthropic API returns rate limit headers
"""
import os
import json
from anthropic import Anthropic

def test_rate_limit_headers():
    """Make a minimal API call and inspect response headers."""

    # Check for API key
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("❌ ANTHROPIC_API_KEY not set")
        return None

    print(f"✓ API key found (ends with ...{api_key[-4:]})")

    client = Anthropic()

    print("\n📡 Making minimal API request...")

    # Make minimal request - using with_raw_response to get headers
    with client.messages.with_raw_response.create(
        model="claude-sonnet-4-20250514",
        max_tokens=10,
        messages=[{"role": "user", "content": "Say 'ok'"}]
    ) as response:
        # Get all headers
        headers = dict(response.headers)

        print(f"\n✓ Response status: {response.status_code}")

        # Filter for rate limit headers
        rate_limit_headers = {
            k: v for k, v in headers.items()
            if 'ratelimit' in k.lower() or 'retry' in k.lower()
        }

        print("\n" + "="*60)
        print("RATE LIMIT HEADERS FOUND:")
        print("="*60)

        if rate_limit_headers:
            for key, value in sorted(rate_limit_headers.items()):
                print(f"  {key}: {value}")
        else:
            print("  ❌ No rate limit headers found!")
            print("\n  All headers received:")
            for key, value in sorted(headers.items()):
                print(f"    {key}: {value}")

        print("\n" + "="*60)

        # Parse the actual response content
        content = response.read()
        data = json.loads(content)

        print("\nUSAGE FROM RESPONSE BODY:")
        print("="*60)
        if 'usage' in data:
            print(f"  input_tokens: {data['usage'].get('input_tokens')}")
            print(f"  output_tokens: {data['usage'].get('output_tokens')}")

        return rate_limit_headers

if __name__ == "__main__":
    headers = test_rate_limit_headers()

    if headers:
        print("\n✅ SUCCESS: Rate limit headers are available!")
        print("   We can use these to track subscription limits.")
    else:
        print("\n⚠️  No rate limit headers found - may need different approach")
