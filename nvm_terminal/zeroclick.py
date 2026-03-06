"""ZeroClick.ai integration — signal collection, offers, and ASCII ad rendering."""
import json
import uuid
import threading
import requests
from openai import OpenAI
from .state import AppState
from .ui import console

ZC_OFFERS_URL = "https://zeroclick.dev/api/v2/offers"
ZC_MCP_URL = "https://zeroclick.dev/mcp/v2"
ZC_IMPRESSIONS_URL = "https://zeroclick.dev/api/v2/impressions"

# Per-session IDs for ZeroClick user profiling
_SESSION_ID = f"nvm-{uuid.uuid4().hex[:8]}"
_USER_ID = f"nvm-user-{uuid.uuid4().hex[:8]}"

# Accumulated signals this session
_signals_lock = threading.Lock()
_all_signals: list[dict] = []

SIGNAL_CATEGORIES = [
    "interest", "evaluation", "purchase_intent", "problem",
    "price_sensitivity", "brand_affinity", "user_context",
    "business_context", "recommendation_request",
]

EXTRACT_PROMPT = """Extract commercial intent signals from this user message.
Return a JSON array of signals (or [] if no commercial intent).

Each signal: {{"category": "<one of {categories}>", "subject": "<brief, max 80 chars>", "confidence": 0.0-1.0, "sentiment": "positive|negative|neutral"}}

Examples:
- "I need a new laptop" → [{{"category":"purchase_intent","subject":"laptop","confidence":0.9,"sentiment":"positive"}}]
- "Compare AWS vs GCP" → [{{"category":"evaluation","subject":"AWS vs GCP cloud hosting","confidence":0.8,"sentiment":"neutral"}}]
- "hello" → []

Return ONLY the JSON array."""

# ASCII art templates for product categories
ASCII_ART = {
    "shoes": (
        "    __\n"
        "   / _)\n"
        "  / /\n"
        " / /___\n"
        "/_____/"
    ),
    "laptop": (
        "  .-----------.\n"
        "  |  _______  |\n"
        "  | |       | |\n"
        "  | |_______| |\n"
        "  |___________|\n"
        "  /___________\\"
    ),
    "phone": (
        "  .-------.\n"
        "  |       |\n"
        "  |       |\n"
        "  |       |\n"
        "  |  ___  |\n"
        "  |_|   |_|"
    ),
    "headphones": (
        "    ___   ___\n"
        "   /   \\_/   \\\n"
        "  |           |\n"
        "  |  ()   ()  |\n"
        "   \\         /\n"
        "    \\_______/"
    ),
    "camera": (
        "   ___________\n"
        "  /    ____   \\\n"
        " |   /    \\   |\n"
        " |  | (OO) |  |\n"
        " |   \\____/   |\n"
        "  \\___________/"
    ),
    "default": (
        "   ________\n"
        "  /        \\\n"
        " |  [DEAL]  |\n"
        " |          |\n"
        "  \\________/"
    ),
}


def _pick_art(title: str, subject: str = "") -> str:
    """Pick ASCII art based on product keywords."""
    text = f"{title} {subject}".lower()
    if any(w in text for w in ("shoe", "sneaker", "boot", "running", "nike", "adidas")):
        return ASCII_ART["shoes"]
    if any(w in text for w in ("laptop", "computer", "macbook", "thinkpad", "dell", "notebook")):
        return ASCII_ART["laptop"]
    if any(w in text for w in ("phone", "iphone", "samsung", "pixel", "mobile")):
        return ASCII_ART["phone"]
    if any(w in text for w in ("headphone", "earbuds", "airpod", "audio", "speaker")):
        return ASCII_ART["headphones"]
    if any(w in text for w in ("camera", "photo", "canon", "sony", "lens")):
        return ASCII_ART["camera"]
    return ASCII_ART["default"]


def _stars(value: float, scale: float = 5) -> str:
    """Render star rating as ASCII."""
    full = int(value)
    half = 1 if (value - full) >= 0.25 else 0
    empty = int(scale) - full - half
    return "★" * full + ("½" if half else "") + "☆" * empty


def extract_signals(api_key: str, user_message: str) -> list[dict]:
    """Use LLM to extract commercial intent signals from user message."""
    if not api_key:
        return []
    try:
        client = OpenAI(api_key=api_key)
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": EXTRACT_PROMPT.format(categories=SIGNAL_CATEGORIES)},
                {"role": "user", "content": user_message},
            ],
            max_tokens=300,
            temperature=0,
        )
        text = resp.choices[0].message.content.strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[1].rsplit("```", 1)[0].strip()
        return json.loads(text)
    except Exception:
        return []


def broadcast_signals(zc_api_key: str, signals: list[dict]) -> bool:
    """Send signals to ZeroClick MCP Signal Server."""
    if not signals or not zc_api_key:
        return False
    try:
        resp = requests.post(
            ZC_MCP_URL,
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json, text/event-stream",
                "x-zc-api-key": zc_api_key,
                "x-zc-llm-model": "openai/gpt-4o-mini",
                "x-zc-user-id": _USER_ID,
                "x-zc-user-session-id": _SESSION_ID,
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
    except Exception:
        return False


def process_signals(state: AppState, user_message: str) -> list[dict]:
    """Extract signals from user message and broadcast to ZeroClick (async).

    Returns the extracted signals for display/use.
    """
    oai_key = state.config.get("openai_api_key", "")
    zc_key = state.config.get("zeroclick_api_key", "")
    if not oai_key or not zc_key:
        return []

    signals = extract_signals(oai_key, user_message)
    if not signals:
        return []

    # Store locally
    with _signals_lock:
        _all_signals.extend(signals)

    # Broadcast in background thread
    def _send():
        broadcast_signals(zc_key, signals)

    threading.Thread(target=_send, daemon=True).start()

    return signals


def get_all_signals() -> list[dict]:
    """Return all accumulated signals this session."""
    with _signals_lock:
        return list(_all_signals)


def fetch_offers(zc_api_key: str, query: str, signals: list[dict] | None = None, limit: int = 3) -> list[dict]:
    """Fetch personalized offers from ZeroClick."""
    if not zc_api_key:
        return []
    body: dict = {
        "method": "client",
        "query": query,
        "limit": limit,
    }
    if signals:
        body["signals"] = signals[-5:]  # last 5 signals for context
    try:
        resp = requests.post(
            ZC_OFFERS_URL,
            headers={
                "Content-Type": "application/json",
                "x-zc-api-key": zc_api_key,
            },
            json=body,
            timeout=10,
        )
        if resp.status_code == 200:
            data = resp.json()
            if isinstance(data, list):
                return data
            return data.get("offers", data.get("results", []))
    except Exception:
        pass
    return []


def track_impressions(offer_ids: list[str]):
    """Track offer impressions (fire and forget in background)."""
    if not offer_ids:
        return

    def _track():
        try:
            requests.post(
                ZC_IMPRESSIONS_URL,
                headers={"Content-Type": "application/json"},
                json={"ids": offer_ids},
                timeout=5,
            )
        except Exception:
            pass

    threading.Thread(target=_track, daemon=True).start()


def render_offers(offers: list[dict]):
    """Render offers as ASCII art panels in the terminal."""
    if not offers:
        return

    from rich.panel import Panel
    from rich import box

    offer_ids = []
    panels = []

    for offer in offers:
        offer_id = offer.get("id", "")
        if offer_id:
            offer_ids.append(offer_id)

        title = offer.get("title", "Special Offer")
        subtitle = offer.get("subtitle", "")
        cta = offer.get("cta", "Check it out")
        click_url = offer.get("clickUrl", "")
        content_text = offer.get("content", "")

        # Brand
        brand = offer.get("brand", {})
        brand_name = brand.get("name", "") if isinstance(brand, dict) else ""

        # Price
        price = offer.get("price", {})
        price_str = ""
        if isinstance(price, dict):
            amt = price.get("amount", "")
            curr = price.get("currency", "$")
            orig = price.get("originalPrice", "")
            disc = price.get("discount", "")
            if amt:
                price_str = f"{curr} {amt}"
                if orig and str(orig) != str(amt):
                    price_str += f" [dim strikethrough](was {curr} {orig})[/dim strikethrough]"
                if disc:
                    price_str += f" [bold green]-{disc}[/bold green]"

        # Rating
        rating = offer.get("rating", {})
        rating_str = ""
        if isinstance(rating, dict) and rating.get("value"):
            stars = _stars(rating["value"], rating.get("scale", 5))
            count = rating.get("count", "")
            rating_str = f"{stars} {rating['value']}"
            if count:
                rating_str += f" ({count} reviews)"

        # Pick ASCII art
        art = _pick_art(title, subtitle)

        # Build panel content using Text objects to avoid markup issues
        from rich.text import Text as RichText
        content = RichText()
        content.append(art, style="bright_cyan")
        content.append("\n\n")
        content.append(title, style="bold bright_white")
        content.append("\n")
        if subtitle:
            content.append(subtitle[:60], style="dim")
            content.append("\n")
        if brand_name:
            content.append(brand_name, style="yellow")
            content.append("\n")
        if price_str:
            # Price may have Rich markup for strikethrough/discount
            content.append("\n")
            if isinstance(price, dict):
                amt = price.get("amount", "")
                curr = price.get("currency", "$")
                orig = price.get("originalPrice", "")
                disc = price.get("discount", "")
                if amt:
                    content.append(f"{curr} {amt}", style="bold green")
                    if orig and str(orig) != str(amt):
                        content.append(f" (was {curr} {orig})", style="dim strikethrough")
                    if disc:
                        content.append(f" -{disc}", style="bold green")
            content.append("\n")
        if rating_str:
            content.append(rating_str, style="bright_yellow")
            content.append("\n")
        if content_text:
            short = content_text[:100] + ("..." if len(content_text) > 100 else "")
            content.append("\n")
            content.append(short, style="dim")
            content.append("\n")
        content.append("\n")
        if click_url:
            content.append(f"[{cta}]", style="bold cyan")
            content.append(f" -> {click_url}", style="dim")

        panel = Panel(
            content,
            border_style="bright_cyan",
            box=box.DOUBLE_EDGE,
            width=52,
            padding=(1, 2),
        )
        panels.append(panel)

    # Print header
    console.print("\n[bold bright_cyan]━━━ Sponsored Offers ━━━[/bold bright_cyan]")
    for p in panels:
        console.print(p)

    # Track impressions
    track_impressions(offer_ids)


def maybe_show_offers(state: AppState, signals: list[dict]):
    """If signals indicate commercial intent, fetch and display offers."""
    zc_key = state.config.get("zeroclick_api_key", "")
    if not zc_key or not signals:
        return

    # Only show offers for high-intent signals
    high_intent = ("purchase_intent", "evaluation", "recommendation_request", "interest")
    intent_signals = [s for s in signals if s.get("category") in high_intent]
    if not intent_signals:
        return

    # Use the first signal's subject as query
    query = intent_signals[0].get("subject", "trending products")
    offers = fetch_offers(zc_key, query, get_all_signals())
    render_offers(offers)
