#!/bin/bash
#
# trinity-listen.sh - Blocks until a Trinity event arrives
#
# Trinity Connect: Real-time event listening for local Claude Code integration
#
# Usage:
#   trinity-listen.sh                    # Listen for all events
#   trinity-listen.sh my-agent           # Filter to specific agent
#   trinity-listen.sh all completed      # Filter by event state
#
# Environment Variables:
#   TRINITY_API_KEY    - Required: Your MCP API key (starts with trinity_mcp_)
#   TRINITY_WS_URL     - Optional: WebSocket URL (default: ws://localhost:8000/ws/events)
#
# Exit Codes:
#   0 - Event received and printed
#   1 - Configuration error (missing API key, missing tools)
#   2 - Connection error
#
# Example:
#   export TRINITY_API_KEY="trinity_mcp_xxx"
#   ./trinity-listen.sh my-research-agent completed
#

set -e

# Configuration
TRINITY_WS="${TRINITY_WS_URL:-ws://localhost:8000/ws/events}"
API_KEY="${TRINITY_API_KEY:-}"
AGENT_FILTER="${1:-all}"
STATE_FILTER="${2:-all}"  # all, completed, failed, started

# Validate API key
if [ -z "$API_KEY" ]; then
    echo "Error: TRINITY_API_KEY environment variable required" >&2
    echo "" >&2
    echo "Get your API key from Trinity Settings -> API Keys page" >&2
    echo "Then export it:" >&2
    echo "  export TRINITY_API_KEY=\"trinity_mcp_xxx\"" >&2
    exit 1
fi

if [[ ! "$API_KEY" =~ ^trinity_mcp_ ]]; then
    echo "Error: API key must start with 'trinity_mcp_'" >&2
    exit 1
fi

# Find WebSocket tool
WS_TOOL=""
if command -v websocat &> /dev/null; then
    WS_TOOL="websocat"
elif command -v wscat &> /dev/null; then
    WS_TOOL="wscat"
else
    echo "Error: websocat or wscat required" >&2
    echo "" >&2
    echo "Install one of:" >&2
    echo "  brew install websocat           # macOS" >&2
    echo "  cargo install websocat          # Rust/Cargo" >&2
    echo "  npm install -g wscat            # Node.js" >&2
    exit 1
fi

# Validate jq is available for JSON parsing
if ! command -v jq &> /dev/null; then
    echo "Error: jq required for JSON parsing" >&2
    echo "" >&2
    echo "Install with:" >&2
    echo "  brew install jq                 # macOS" >&2
    echo "  apt-get install jq              # Debian/Ubuntu" >&2
    exit 1
fi

echo "Trinity Connect: Listening for events (agent: $AGENT_FILTER, state: $STATE_FILTER)..." >&2
echo "WebSocket: $TRINITY_WS" >&2
echo "Press Ctrl+C to stop" >&2
echo "" >&2

# Process events
process_event() {
    local line="$1"

    # Parse event type
    local event_type=$(echo "$line" | jq -r '.type // empty' 2>/dev/null)

    # Skip connection confirmations (log them but don't exit)
    if [ "$event_type" = "connected" ]; then
        local user=$(echo "$line" | jq -r '.user // "unknown"' 2>/dev/null)
        local agent_count=$(echo "$line" | jq -r '.accessible_agents | length // 0' 2>/dev/null)
        echo "Connected as: $user (can see $agent_count agents)" >&2
        return 1  # Continue listening
    fi

    if [ "$event_type" = "refreshed" ]; then
        echo "Agent list refreshed" >&2
        return 1  # Continue listening
    fi

    # Extract agent name (different fields for different event types)
    local agent=$(echo "$line" | jq -r '
        .agent_name //
        .agent //
        .name //
        .data.name //
        .details.source_agent //
        .details.target_agent //
        empty
    ' 2>/dev/null)

    # Extract state (different fields for different event types)
    local state=$(echo "$line" | jq -r '
        .activity_state //
        .status //
        (if .type == "agent_started" then "started" else empty end) //
        (if .type == "agent_stopped" then "stopped" else empty end) //
        empty
    ' 2>/dev/null)

    # Apply agent filter
    if [ "$AGENT_FILTER" != "all" ] && [ "$agent" != "$AGENT_FILTER" ]; then
        return 1  # Continue listening
    fi

    # Apply state filter
    if [ "$STATE_FILTER" != "all" ] && [ "$state" != "$STATE_FILTER" ]; then
        return 1  # Continue listening
    fi

    # Event matches! Output it
    echo "=== TRINITY EVENT ==="
    echo "$line" | jq .
    echo "=== END EVENT ==="

    return 0  # Exit with success
}

# Connect and listen for events
if [ "$WS_TOOL" = "websocat" ]; then
    # websocat is preferred - more reliable for scripting
    websocat --text --no-close "${TRINITY_WS}?token=${API_KEY}" 2>/dev/null | \
    while IFS= read -r line; do
        if process_event "$line"; then
            # Kill the parent websocat process
            pkill -P $$ websocat 2>/dev/null || true
            exit 0
        fi
    done

    exit_code=$?
    if [ $exit_code -ne 0 ]; then
        echo "Connection closed or error occurred" >&2
        exit 2
    fi
else
    # wscat fallback
    wscat -c "${TRINITY_WS}?token=${API_KEY}" 2>/dev/null | \
    while IFS= read -r line; do
        if process_event "$line"; then
            # Kill the parent wscat process
            pkill -P $$ wscat 2>/dev/null || true
            exit 0
        fi
    done

    exit_code=$?
    if [ $exit_code -ne 0 ]; then
        echo "Connection closed or error occurred" >&2
        exit 2
    fi
fi
