# Timezone Handling in Trinity

> **Last Updated**: 2026-01-15
> **Status**: Implemented

## The Problem

When the server runs in a different timezone than the user:
- Server stores timestamp: `"2026-01-15T10:30:00"` (no timezone indicator)
- JavaScript's `new Date("2026-01-15T10:30:00")` interprets it as **local time**
- Result: Events appear hours in the past/future on the Dashboard Timeline

## The Solution

**All timestamps must include 'Z' suffix (or explicit offset) to indicate UTC.**

```javascript
// Without 'Z' - WRONG (interpreted as local time)
new Date("2026-01-15T10:30:00")

// With 'Z' - CORRECT (interpreted as UTC)
new Date("2026-01-15T10:30:00Z")
```

## Implementation

### Backend (Python)

Use the timestamp utilities in `src/backend/utils/helpers.py`:

```python
from utils.helpers import utc_now_iso, to_utc_iso, parse_iso_timestamp

# Get current UTC time as ISO string with 'Z' suffix
timestamp = utc_now_iso()  # "2026-01-15T10:30:00.123456Z"

# Convert datetime to UTC ISO string
from datetime import datetime
dt = datetime.now()
timestamp = to_utc_iso(dt)  # "2026-01-15T10:30:00.123456Z"

# Parse ISO timestamp (handles both 'Z' and non-'Z')
dt = parse_iso_timestamp("2026-01-15T10:30:00")  # Returns UTC datetime
dt = parse_iso_timestamp("2026-01-15T10:30:00Z") # Also works
```

**DON'T use:**
```python
# These produce timestamps without 'Z' suffix - AVOID
datetime.utcnow().isoformat()  # "2026-01-15T10:30:00.123456"
datetime.now().isoformat()     # "2026-01-15T10:30:00.123456"
```

### Frontend (JavaScript)

Use the timestamp utilities in `src/frontend/src/utils/timestamps.js`:

```javascript
import { parseUTC, getTimestampMs, formatLocalTime } from '@/utils/timestamps'

// Parse backend timestamp (handles missing 'Z')
const date = parseUTC("2026-01-15T10:30:00")  // Correctly interprets as UTC

// Get Unix timestamp for calculations
const ms = getTimestampMs("2026-01-15T10:30:00")  // Milliseconds since epoch

// Display in user's local timezone
formatLocalTime("2026-01-15T10:30:00Z")  // "10:30:00 AM" (in user's timezone)
```

For Vue composables, use `src/frontend/src/composables/useFormatters.js`:

```javascript
import { useFormatters } from '@/composables/useFormatters'

const { parseUTCTimestamp, formatLocalDateTime } = useFormatters()
```

**DON'T use:**
```javascript
// This misinterprets timestamps without 'Z' as local time - AVOID
new Date(backendTimestamp).getTime()

// Instead use:
getTimestampMs(backendTimestamp)
parseUTC(backendTimestamp).getTime()
```

## Key Files

| File | Purpose |
|------|---------|
| `src/backend/utils/helpers.py` | Backend timestamp utilities |
| `src/frontend/src/utils/timestamps.js` | Frontend timestamp utilities (for stores) |
| `src/frontend/src/composables/useFormatters.js` | Frontend utilities (for components) |

## Database Considerations

SQLite stores timestamps as TEXT. Existing data may not have 'Z' suffix. The parsing utilities handle both formats:

```python
# parse_iso_timestamp handles both:
parse_iso_timestamp("2026-01-15T10:30:00")   # Old format (no Z)
parse_iso_timestamp("2026-01-15T10:30:00Z")  # New format (with Z)
```

## Timeline-Specific Logic

The Dashboard Timeline (`ReplayTimeline.vue`) uses these utilities for:

1. **Positioning events on the timeline:**
   ```javascript
   const startTimestamp = getTimestampMs(event.timestamp)
   const x = ((startTimestamp - startTime) / duration) * gridWidth
   ```

2. **Displaying relative times:**
   ```javascript
   const date = parseUTC(timestamp)
   const diff = Date.now() - date.getTime()
   ```

3. **Computing time ranges:**
   ```javascript
   const startTime = getTimestampMs(props.timelineStart)
   const endTime = getTimestampMs(props.timelineEnd)
   ```

## Testing

To verify timezone handling works correctly:

1. **Server in different timezone:** Deploy to a server in UTC while testing from a different timezone
2. **Check Dashboard Timeline:** Execute a task and verify it appears at the correct position
3. **Check relative times:** "Just now" should show for recent events, not "X hours ago"

## Common Issues

### Events appear hours in the past
**Cause:** Timestamp parsed without 'Z' suffix
**Fix:** Use `parseUTC()` or `getTimestampMs()` instead of `new Date()`

### Duration calculations are wrong
**Cause:** Mixing local and UTC times in subtraction
**Fix:** Always use `getTimestampMs()` for both timestamps

### API returns timestamps without 'Z'
**Cause:** Using `datetime.utcnow().isoformat()` directly
**Fix:** Use `utc_now_iso()` helper

## Summary

| Layer | Use | Don't Use |
|-------|-----|-----------|
| Backend (create) | `utc_now_iso()` | `datetime.utcnow().isoformat()` |
| Backend (convert) | `to_utc_iso(dt)` | `dt.isoformat()` |
| Backend (parse) | `parse_iso_timestamp(s)` | `datetime.fromisoformat(s)` |
| Frontend (parse) | `parseUTC(s)` | `new Date(s)` |
| Frontend (calc) | `getTimestampMs(s)` | `new Date(s).getTime()` |
| Frontend (display) | `formatLocalTime(s)` | `new Date(s).toLocaleString()` |
