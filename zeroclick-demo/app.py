"""
ZeroClick.ai Demo — Conversational agent that learns user preferences
via signal collection and serves relevant offers.

Usage:
    python app.py
"""
import json
import os
import uuid

import requests
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

ZC_API_KEY = os.environ["ZEROCLICK_API_KEY"]
OPENAI_API_KEY = os.environ["OPENAI_API_KEY"]

ZC_OFFERS_URL = "https://zeroclick.dev/api/v2/offers"
ZC_SIGNALS_URL = "https://zeroclick.dev/api/v2/signals"
ZC_MCP_URL = "https://zeroclick.dev/mcp/v2"

llm = OpenAI(api_key=OPENAI_API_KEY)

# Persistent user/session IDs so ZeroClick can build a profile
USER_ID = f"demo-user-{uuid.uuid4().hex[:8]}"
SESSION_ID = f"session-{uuid.uuid4().hex[:8]}"

SIGNAL_CATEGORIES = [
    "interest", "evaluation", "purchase_intent", "problem",
    "price_sensitivity", "brand_affinity", "user_context",
    "business_context", "recommendation_request",
]

EXTRACT_SIGNALS_PROMPT = """You are a signal extraction engine. Given a user message from a conversation,
extract commercial intent signals. Return a JSON array of signals (or empty array if none).

Each signal has:
- "category": one of {categories}
- "subject": brief description (max 100 chars)
- "confidence": 0.0-1.0
- "sentiment": "positive", "negative", or "neutral"

Examples:
- "I need new running shoes" → [{{"category":"purchase_intent","subject":"running shoes","confidence":0.9,"sentiment":"positive"}}]
- "Is the MacBook Pro worth it?" → [{{"category":"evaluation","subject":"MacBook Pro","confidence":0.8,"sentiment":"neutral"}}]
- "Just chatting" → []

Return ONLY the JSON array, no other text."""

CHAT_SYSTEM = """You are a helpful shopping/lifestyle assistant. You help users explore products,
compare options, and make purchase decisions. Be conversational and helpful.
When you notice the user has preferences or interests, naturally explore those topics deeper."""


def extract_signals(user_message: str) -> list[dict]:
    """Use LLM to extract commercial intent signals from user message."""
    try:
        resp = llm.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": EXTRACT_SIGNALS_PROMPT.format(categories=SIGNAL_CATEGORIES)},
                {"role": "user", "content": user_message},
            ],
            max_tokens=300,
            temperature=0,
        )
        text = resp.choices[0].message.content.strip()
        # Strip markdown fences if present
        if text.startswith("```"):
            text = text.split("\n", 1)[1].rsplit("```", 1)[0].strip()
        return json.loads(text)
    except Exception as e:
        print(f"  [signal extraction error: {e}]")
        return []


def broadcast_signals_mcp(signals: list[dict]) -> bool:
    """Send signals via ZeroClick MCP Signal Server."""
    if not signals:
        return False
    try:
        resp = requests.post(
            ZC_MCP_URL,
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json, text/event-stream",
                "x-zc-api-key": ZC_API_KEY,
                "x-zc-llm-model": "openai/gpt-4o-mini",
                "x-zc-user-id": USER_ID,
                "x-zc-user-session-id": SESSION_ID,
                "x-zc-user-locale": "en-US",
            },
            json={
                "jsonrpc": "2.0",
                "method": "tools/call",
                "params": {
                    "name": "broadcast_signal",
                    "arguments": {"signals": signals},
                },
                "id": 1,
            },
            timeout=10,
        )
        return resp.status_code == 200
    except Exception as e:
        print(f"  [MCP broadcast error: {e}]")
        return False


def broadcast_signals_rest(signals: list[dict]) -> bool:
    """Send signals via ZeroClick REST API (fallback)."""
    if not signals:
        return False
    try:
        resp = requests.post(
            ZC_SIGNALS_URL,
            headers={
                "Content-Type": "application/json",
                "x-zc-api-key": ZC_API_KEY,
            },
            json={
                "userId": USER_ID,
                "signals": signals,
            },
            timeout=10,
        )
        return resp.status_code in (200, 204)
    except Exception as e:
        print(f"  [REST signal error: {e}]")
        return False


def fetch_offers(query: str, signals: list[dict] | None = None, limit: int = 3) -> list[dict]:
    """Fetch personalized offers from ZeroClick."""
    body = {
        "method": "client",
        "query": query,
        "limit": limit,
    }
    if signals:
        body["signals"] = signals
    try:
        resp = requests.post(
            ZC_OFFERS_URL,
            headers={
                "Content-Type": "application/json",
                "x-zc-api-key": ZC_API_KEY,
            },
            json=body,
            timeout=10,
        )
        if resp.status_code == 200:
            data = resp.json()
            # Response could be a list or {"offers": [...]}
            if isinstance(data, list):
                return data
            return data.get("offers", data.get("results", []))
        else:
            print(f"  [offers API {resp.status_code}: {resp.text[:200]}]")
            return []
    except Exception as e:
        print(f"  [offers error: {e}]")
        return []


def display_offers(offers: list[dict]):
    """Pretty-print offers."""
    if not offers:
        return
    print()
    print("  ╭─── Relevant Offers ───╮")
    for i, offer in enumerate(offers, 1):
        title = offer.get("title", "Untitled")
        subtitle = offer.get("subtitle", "")
        cta = offer.get("cta", "")
        click_url = offer.get("clickUrl", "")
        brand = offer.get("brand", {})
        brand_name = brand.get("name", "") if isinstance(brand, dict) else ""
        price = offer.get("price", {})
        price_str = ""
        if isinstance(price, dict) and price.get("amount"):
            price_str = f" — ${price['amount']}"

        print(f"  │ {i}. {title}{price_str}")
        if subtitle:
            print(f"  │    {subtitle}")
        if brand_name:
            print(f"  │    Brand: {brand_name}")
        if cta and click_url:
            print(f"  │    [{cta}] → {click_url}")
        if i < len(offers):
            print("  │")
    print("  ╰─────────────────────────╯")


def chat_response(conversation: list[dict]) -> str:
    """Get chat response from LLM."""
    resp = llm.chat.completions.create(
        model="gpt-4o-mini",
        messages=conversation,
        max_tokens=500,
    )
    return resp.choices[0].message.content


def main():
    print("=" * 55)
    print("  ZeroClick.ai Demo — Smart Preference Learning")
    print("=" * 55)
    print(f"  User ID:    {USER_ID}")
    print(f"  Session ID: {SESSION_ID}")
    print()
    print("  Chat naturally. I'll learn your preferences and")
    print("  show relevant offers as we talk.")
    print()
    print("  Commands: /offers <query>, /signals, /quit")
    print()

    conversation = [{"role": "system", "content": CHAT_SYSTEM}]
    all_signals: list[dict] = []

    while True:
        try:
            user_input = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nBye!")
            break

        if not user_input:
            continue

        if user_input.lower() in ("/quit", "/exit", "quit", "exit"):
            print("Bye!")
            break

        # Manual offers fetch
        if user_input.lower().startswith("/offers"):
            query = user_input[7:].strip() or "trending products"
            print(f"  Fetching offers for: {query}")
            offers = fetch_offers(query, all_signals[-5:] if all_signals else None)
            display_offers(offers)
            if not offers:
                print("  No offers returned.")
            print()
            continue

        # Show collected signals
        if user_input.lower() == "/signals":
            if not all_signals:
                print("  No signals collected yet.\n")
            else:
                print(f"  {len(all_signals)} signals collected:")
                for s in all_signals:
                    print(f"    [{s['category']}] {s['subject']} "
                          f"(conf={s.get('confidence', '?')}, sent={s.get('sentiment', '?')})")
                print()
            continue

        # 1. Extract signals from user message
        signals = extract_signals(user_input)
        if signals:
            all_signals.extend(signals)
            tags = ", ".join(f"{s['category']}:{s['subject']}" for s in signals)
            print(f"  📡 Signals: {tags}")

            # 2. Broadcast to ZeroClick
            ok = broadcast_signals_mcp(signals)
            if not ok:
                ok = broadcast_signals_rest(signals)
            status = "sent" if ok else "failed"
            print(f"  📡 Broadcast: {status}")

        # 3. Chat response
        conversation.append({"role": "user", "content": user_input})
        reply = chat_response(conversation)
        conversation.append({"role": "assistant", "content": reply})
        print(f"\nAssistant: {reply}")

        # 4. If commercial intent detected, also fetch offers
        if signals and any(s["category"] in ("purchase_intent", "evaluation", "recommendation_request") for s in signals):
            query = signals[0]["subject"]
            offers = fetch_offers(query, signals)
            display_offers(offers)

        print()


if __name__ == "__main__":
    main()
